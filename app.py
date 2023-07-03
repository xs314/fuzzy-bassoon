from villa import Bot
from villa.event import SendMessageEvent
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import models
import uvicorn
import utils
from deta import Deta

import time,requests,json,random,secrets
from pydantic import BaseModel
from typing import Union
from enum import Enum



deta = Deta()
db_papers=deta.Base('papers')
db_attempts=deta.Base('attempts')
db_vila_quizrole_cfg=deta.Base('vila_quizrole_cfg')
db_vila_user_role_attempts=deta.Base('vila_user_role_att')

app = FastAPI()

bot = Bot(bot_id=os.environ.get('bot_id'), bot_secret=os.environ.get('bot_secret'), callback_url=os.environ.get('bot_callback'),wait_util_complete=True)
# 初始化Bot，填写你的bot_id、密钥以及回调地址endpoint
# 举例：若申请时提供的回调地址为https://域名/callback，这里的callback_url就填`/callback`

@bot.on_startswith("ping",prefix='/')
async def alive(event: SendMessageEvent):
    await event.send('pong',mention_sender=True)
    return
    
@bot.on_startswith("扔漂流瓶",prefix='/')
async def throw(event: SendMessageEvent):        
    msg = await utils.put_bottle(event,bot)
    await event.send(msg,mention_sender=True,quote_message=True)
    return
    # 一个简单的处理函数，向你的Bot发送包含`hello`关键词的消息，它将会回复你`world`！

@bot.on_startswith("捡漂流瓶",prefix='/')
async def fetch(event: SendMessageEvent):

    msg = await utils.random_bottle()
    await event.send(msg,mention_sender=True)
    return

@bot.on_startswith("setquizRole",prefix='/')
async def setpaper(event: SendMessageEvent):
    #this needs an admin so we check is it admin or owner?
    member=await bot.get_member(event.villa_id,event.from_user_id)
    member_roles=member.role_list
    is_admin=False
    for role in member_roles:
        if role.role_type=='MEMBER_ROLE_TYPE_ADMIN' or role.role_type=='MEMBER_ROLE_TYPE_OWNER':
            is_admin=True
            break
    if not is_admin:
        await event.send('只有admin或owner允许使用此操作',mention_sender=True,quote_message=True)
    par=event.message.get_plain_text()
    params=' '.join(par.split('/setquizRole')[1].split(' ')[1:])
    print(params.split(' '))
    state=utils.get_cmd_state(['setquizRole',event.villa_id])['data']
    #if params is a json,we read the attempts:int , joinTimeReq:int , requiredRole:int
    if params!='' and params[0]=='{':
        try:
            idata=json.loads(params)
            sa={}
            for data in idata:
                title=data['title']
                if not title:
                    await event.send('你应该为你的rule提供一个Title',mention_sender=True,quote_message=True)
                    return
                attempts=int(data['attempts'])
                joinTimeReq=int(data['joinTimeReq'])
                requiredRole=int(data['requiredRole'])
                successRole=int(data['successRole'])
                paperID=data['paperId']
                if not db_papers.get(paperID):
                    await event.send('这不是合法的paperID。你应该先去创建paper，然后使用你得到的id',mention_sender=True,quote_message=True)
                    return
                #check do we have this role?
                hasrole=0
                roles_str=''
                villa_roles=await bot.get_villa_member_roles(event.villa_id)
                for i in villa_roles:
                    if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                        continue
                    roles_str+=f'{i.id} = {i.name}\n'
                    if i.id==requiredRole:
                        hasrole+=1
                    if i.id==successRole:
                        hasrole+=1
                if hasrole<2:
                    await event.send(f'没有这些roleid。你的服务器有以下身份组:\n{roles_str}',mention_sender=True,quote_message=True)
                    return
                sa[paperID]={'title':title,'attempts':attempts,'joinTimeReq':joinTimeReq,'requiredRole':requiredRole,'successRole':successRole,'paperId':paperID}
            db_vila_quizrole_cfg.put({'data':sa},str(event.villa_id))
            await event.send('已设置',mention_sender=True,quote_message=True)
            return
        except json.JSONDecodeError:
            pass  
    elif params=='':  
        
        
        if params=='':
            existing_cfg=db_vila_quizrole_cfg.get(str(event.villa_id))
            if not existing_cfg:
                msg='没有已知的quizRole Config。如欲新建，使用/setquizRole new。'
            else:
                existing_cfg=existing_cfg['data']
                msg='以下是现有的config。/setquizRole (edit [ID][<br>key=val...]|new|del [ID])\n'
                for n in existing_cfg.keys():
                    msg+=f'#{n} {existing_cfg[n]["title"]}\n'
            await event.send(msg,mention_sender=True,quote_message=True)
            return
    
    elif params=='new':
        msg='New:0->1 你想如何称呼此规则？此值并没有实际作用，只是方便识别，new/del/edit是保留字。/setquizRole [input]'
        utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'new','step':0,'data':{}})
        await event.send(msg,mention_sender=True,quote_message=True)
    elif params.split(' ')[0]=='del' and params.split(' ')[1]!='':
        if orig:=db_vila_quizrole_cfg.get(str(event.villa_id)):
            if not orig['data'].get(params.split(' ')[1]):
                msg=f"没有此key"
                await event.send(msg,mention_sender=True,quote_message=True)
                return
            del orig['data'][params.split(' ')[1]]
            db_vila_quizrole_cfg.put(orig,str(event.villa_id))
            utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'','step':0,'data':{}}) #否则写回会有问题
            await event.send('-完成。',mention_sender=True,quote_message=True)
        else:
            await event.send('未配置。先new',mention_sender=True,quote_message=True)
            return
    elif params.split(' ')[0]=='edit' and params.split(' ')[1]!='':
        if orig:=db_vila_quizrole_cfg.get(str(event.villa_id)):
            if not orig['data'].get(params.split('\n')[0].split(' ')[1]):
                msg=f"e.没有此key"
                await event.send(msg,mention_sender=True,quote_message=True)
                return
            print('==>',params.split('\n'))
            if len(params.split('\n'))<2:
                msg=f"{orig['data'].get(params.split(' ')[1])}\n以一个回车来开始key=value"
                await event.send(msg,mention_sender=True,quote_message=True)
                return
            for line in params.split('\n')[1:]:

                key=line.split('=')[0]
                val=line.split('=')[1]
                villa_roles=await bot.get_villa_member_roles(event.villa_id)
                roles_str='你的服务器有以下几个身份组:\n'
                for i in villa_roles:
                    if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                        continue
                    roles_str+=f'{i.id} = {i.name}\n'
                #sa.append({'title':title,'attempts':attempts,'joinTimeReq':joinTimeReq,'requiredRole':requiredRole,'successRole':successRole,'paperId':paperID})
                if key=='title':
                    if val=='':
                        await event.send('你应该为你的rule提供一个Title',mention_sender=True,quote_message=True)
                        return
                    orig['data'][params.split('\n')[0].split(' ')[1]]['title']=val
                elif key=='attempts':
                    if int(val)<0:
                        await event.send('attempts的小于0视为0（不限制）',mention_sender=True,quote_message=True)
                        orig['data'][params.split('\n')[0].split(' ')[1]]['attempts']=0
                    else:
                        orig['data'][params.split('\n')[0].split(' ')[1]]['attempts']=int(val)
                elif key=='joinTimeReq':
                    if int(val)<0:
                        await event.send('joinTimeReq的小于0视为0（不除制）',mention_sender=True,quote_message=True)
                        orig['data'][params.split('\n')[0].split(' ')[1]]['joinTimeReq']=0
                    else:
                        orig['data'][params.split('\n')[0].split(' ')[1]]['joinTimeReq']=int(val)
                elif key=='requiredRole':
                    hasRole=False
                    for i in villa_roles:
                        if int(val)==0:
                            hasRole=True
                            break
                        if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                            continue
                        if i.id==int(val):
                            hasRole=True
                            break
                    if not hasRole:
                        await event.send(roles_str,mention_sender=True,quote_message=True)
                        return
                    orig['data'][params.split('\n')[0].split(' ')[1]]['requiredRole']=int(val)
                elif key=='successRole':
                    hasRole=False
                    for i in villa_roles:
                        if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                            continue
                        if i.id==int(val):
                            hasRole=True
                            break
                    if not hasRole:
                        await event.send(roles_str,mention_sender=True,quote_message=True)
                        return
                    orig['data'][params.split('\n')[0].split(' ')[1]]['successRole']=int(val)
                elif key=='paperId':
                    if not db_papers.get(val):
                        await event.send('这不是合法的paperID。你应该先去创建paper，然后使用你得到的id',mention_sender=True,quote_message=True)
                        return
                    orig['data'][params.split('\n')[0].split(' ')[1]]['paperId']=val
            db_vila_quizrole_cfg.put(orig,str(event.villa_id))
            await event.send('>完成',mention_sender=True,quote_message=True)
            return
        else:
            await event.send('未配置。先new',mention_sender=True,quote_message=True)
            return
    elif state and state['action']!='':

        villa_roles=await bot.get_villa_member_roles(event.villa_id)
        roles_str='\n你的服务器有以下几个身份组:\n'
        for i in villa_roles:
            if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                continue
            roles_str+=f'{i.id} = {i.name}\n'
        if state['action']=='new':
            #sa.append({'title':title,'attempts':attempts,'joinTimeReq':joinTimeReq,'requiredRole':requiredRole,'successRole':successRole,'paperId':paperID})
            if state['step']==0 and params!='':
                od=state['data']
                od['title']=params
                utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'new','step':1,'data':od})
                await event.send('New:1->2 配置允许的尝试次数，超过此次数仍然可以答题，但将不会计入身份组。0=不限制。',mention_sender=True,quote_message=True)
                return
            elif state['step']==1 and params!='' and int(params)>=0:
                od=state['data']
                od['attempts']=int(params)
                utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'new','step':2,'data':od})
                await event.send('New:2->3 配置要求加入的时间，小于此时间仍然可以答题，但将不会计入身份组。0=不除制。',mention_sender=True,quote_message=True)
            elif state['step']==2 and params!='' and int(params)>=0:
                od=state['data']
                od['joinTimeReq']=int(params)
                utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'new','step':3,'data':od})
                await event.send('New:3->4 配置获取身份组所需的身份组id。0=不限制'+roles_str,mention_sender=True,quote_message=True)
            elif state['step']==3 and params!='' and int(params)>=0:
                od=state['data']
                od['requiredRole']=int(params)
                inROle=False
                for i in villa_roles:
                    if int(params)==0:
                        inROle=True
                        break
                    if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                        continue
                    if int(params) == i.id:
                        inROle=True
                        break
                if not inROle:
                    await event.send('这不是合法的role',mention_sender=True,quote_message=True)
                    return
                utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'new','step':4,'data':od})
                await event.send('New:4->5 配置获取成功的身份组id（就是说你要给什么身份组）'+roles_str,mention_sender=True,quote_message=True)
            elif state['step']==4 and params!='' and int(params)>=0:
                od=state['data']
                od['successRole']=int(params)
                inROle=False
                for i in villa_roles:
                    if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                        continue
                    if int(params) == i.id:
                        inROle=True
                        break
                if not inROle:
                    await event.send('这不是合法的role',mention_sender=True,quote_message=True)
                    return
                utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'new','step':5,'data':od})
                await event.send('New:5->6 配置paperID。',mention_sender=True,quote_message=True)
            elif state['step']==5 and params!='':
                if not db_papers.get(params):
                    await event.send('这不是合法的paperID。请重试。如果没有，你需要建一个',mention_sender=True,quote_message=True)
                    return
                od=state['data']
                od['paperId']=params
                utils.put_cmd_state(['setquizRole',event.villa_id],{'action':'','step':0,'data':{}})
                #write back to append the cfg
                if not db_vila_quizrole_cfg.get(str(event.villa_id)):
                    db_vila_quizrole_cfg.put({'data':{od['paperId']:od}},str(event.villa_id))
                else:
                    db_vila_quizrole_cfg.update({'data.'+od['paperId']:od},str(event.villa_id))
                await event.send('.完成',mention_sender=True,quote_message=True)
                return
                
@bot.on_startswith("redeemquizRole",prefix='/')
async def setRole(event: SendMessageEvent):
    params=' '.join(event.message.get_plain_text().split('/redeemquizRole')[1].split(' ')[1:])
    if not params:
        await event.send('你应该先获取一个akey，然后在这里作为参数使用。',mention_sender=True,quote_message=True)
        return
    attempt=db_attempts.get(params)
    if not attempt:
        await event.send('找不到此回答。',mention_sender=True,quote_message=True)
        return
    if attempt['used']:
        await event.send('此回答已被使用。',mention_sender=True,quote_message=True)
        return
    if vilacfg:=db_vila_quizrole_cfg.get(str(event.villa_id)):
        if dat:=vilacfg['data'].get(attempt['paperId']):
            member=await bot.get_member(event.villa_id,event.from_user_id)
            member_jointime=member.joined_at
            if dat['successRole'] in member.role_id_list:
                await event.send('你已经在对应的身份组了，没有必要了 ',mention_sender=True,quote_message=True)
                return
        #compare join time req:
            if int(time.time())-int(member_jointime)<int(dat['joinTimeReq']):
                await event.send(f"加入服务器时间过短.还需{round((int(dat['joinTimeReq'])-(int(time.time())-int(member_jointime)))/3600,1)}小时",mention_sender=True,quote_message=True)
                return
        #comapre has role
            if dat['requiredRole']!=0:
                if dat['requiredRole'] not in member.role_id_list:
                    villa_roles=await bot.get_villa_member_roles(event.villa_id)
                    roles_str=''
                    for i in villa_roles:
                        if i.role_type=="MEMBER_ROLE_TYPE_ALL_MEMBER":
                            continue
                        roles_str+=f'{i.id} = {i.name}\n'
                    await event.send(f"不符合身份组要求。需要的身份组：{dat['requiredRole']},附身份组对照:\n{roles_str}",mention_sender=True,quote_message=True)
                    return
            ident=f'{event.villa_id}_{event.from_user_id}'
            if att:=db_vila_user_role_attempts.get(ident):
               if qatts:=att.get(attempt['paperId']):
                    if dat['attempts']!=0 and len(qatts)>=dat['attempts']:
                       await event.send('超出最大尝试次数',mention_sender=True,quote_message=True)
                       return
                    db_vila_user_role_attempts.update({attempt['paperId']:db_vila_user_role_attempts.util.append({"ts":int(time.time()),'akey':params})},ident)
                    qatts=len(qatts)+1
               else:
                   db_vila_user_role_attempts.update({attempt['paperId']:[{'ts':int(time.time()),'akey':params}]},ident)
                   qatts=1
            else:
                db_vila_user_role_attempts.put({attempt['paperId']:[{'ts':int(time.time()),'akey':params}]},ident)
                qatts=1
            if dat['attempts']!=0 and qatts>dat['attempts']:
                await event.send('超出最大尝试次数',mention_sender=True,quote_message=True)
                return
            db_attempts.update({'used':True},params)
            if attempt['passed']:
                try:
                    await bot.operate_member_to_role(event.villa_id,dat['successRole'],event.from_user_id,True)
                except:
                    await event.send('身份组操作出现问题',mention_sender=True,quote_message=True)
                    return
            else:
                await event.send('考卷未通过。',mention_sender=True,quote_message=True)
                return
                
        else:
            await event.send('没有这个quizRole。',mention_sender=True,quote_message=True)
            return
    else:
        await event.send('还没设置过quizRole。',mention_sender=True,quote_message=True)
        return
        
    


#fastapi admintools
@app.get("/bvs85wi1qfb6o1eyrpqv3/api/posts")
async def read_posts(last=None,limit:int = 100):
    return await utils.list_unmoderated_bottles(last,limit)

@app.post('/bvs85wi1qfb6o1eyrpqv3/api/moderate')
async def moderate(moderate_body: models.ModerateBody):
    if moderate_body.action==models.actions.accept:
        result=await utils.moderate_accept(moderate_body.key,bot)
        return {"ok":result}
    elif moderate_body.action==models.actions.deny:
        result=await utils.moderate_deny(moderate_body.key,moderate_body.desc,bot)
        return {"ok":result}
    
@app.post('/api/newPaper')
async def newPaper(paper:models.Paper):
    checkres=utils.check_paper_validity(paper)
    if not checkres[0]:
        return {"ok":False,"reason":checkres[1]}
    passwd=secrets.token_urlsafe()
    res=db_papers.put({"value":paper.json(),"pass":passwd})['key']
    return {"ok":True,"key":res,"pass":passwd}

@app.get('/api/getPaper/{paper_id}')
async def read_paper_basic(paper_id):
    res=db_papers.get(paper_id)['value']

    if not res:
        return {'ok':False,'reason':'no such paper'}
    print(res)
    res=json.loads(res)
    res=models.Paper(**res)
    
    return {'ok':True,'title':res.title,'desc':res.desc,'passCount':res.passCount,"time":res.time}

@app.post('/api/getPaper')
async def read_item(paper:models.PaperRequest):
    #check captcha token
    data = {
        'response': paper.captcha_token,
        'secret': os.environ.get('HCAPTCHA_SECRET'),
    }

    response = requests.post('https://hcaptcha.com/siteverify', data=data)
    if not response.json()['success']:
        return {'ok':False,'reason':'captcha error'}
    res=db_papers.get(paper.key)['value']
    if not res:
        return {'ok':False,'reason':'no such paper'}
    res=json.loads(res)
    res=models.Paper(**res)
    questions=[]
    answers=[]
    for it in res.groups:
        ques=[]
        anss=[]#先存好答案
        data={"title":it.title,"desc":it.desc,"passCount":it.passCount}
        qs=random.sample(it.questions,k=it.count)
        random.shuffle(qs)
        for i in qs:
            ques.append(i.q)
            anss.append(i.a)
        data['questions']=ques
        questions.append(data)
        answers.append(anss)
    key=db_attempts.put({"questions":questions,"answers":answers,"paperId":paper.key,'title':res.title,'desc':res.desc,'passCount':res.passCount,"time":res.time,"ts":int(time.time()),'submit':False,"passed":False,"used":False})['key']
    return {"ok":True,"questions":questions,'title':res.title,'desc':res.desc,'passCount':res.passCount,"time":res.time,'akey':key}

@app.post('/api/answerPaper')
async def answer(paper:models.PaperAnswer):
    res=db_attempts.get(paper.akey)
    if not res:
        return {'ok':False,'reason':'no such attempt'}
    if res['ts']+res['time']<int(time.time()):
        return {'ok':False,'reason':'time out'}
    if res['submit']:
        return {'ok':False,'reason':'already submitted'}
    #validate answers
    correct_ans=0
    passed=True
    for i,ans in enumerate(paper.answers):
        gcorr=0
        for j,a in enumerate(ans.a):
            if a==res['answers'][i][j]:
                gcorr+=1
                correct_ans+=1
        if res['questions'][i]['passCount']>gcorr:
            reason=f'Group#{i} passCount not satisfied,expecting {res["questions"][i]["passCount"]},got {gcorr}'
            passed=False
            break
    if res['passCount']>correct_ans and passed!=False:
        reason=f'PassCount not satisfied,expecting {res["passCount"]},got {correct_ans}'
        passed=False
    elif passed!=False:
        passed=True
        reason='global count satisfied with no group failed'
    db_attempts.update({"passed":passed,"reason":reason,"submit":True},paper.akey)
    return {'ok':True,'akey':paper.akey} #we 

@app.post('/api/getPaperEdit')
async def edit_getp(paper:models.EditPaperRequest):
    if dt:=db_papers.get(paper.key):
        if paper.passwd==dt['pass']:
            return {'ok':True,'value':dt['value']}
    return {'ok':False,'reason':'no such paper or bad passwd'}

@app.post('/api/editPaper/{pid}/{pwd}')
async def newPaper(paper:models.Paper,pid:str,pwd:str):
    checkres=utils.check_paper_validity(paper)
    if not checkres[0]:
        return {"ok":False,"reason":checkres[1]}
    if dt:=db_papers.get(pid):
        if pwd==dt['pass']:
            db_papers.update({"value":paper.json()},pid)
            return {"ok":True,"key":pid}
    return {'ok':False,'reason':'no such paper or bad passwd'}


app.mount("/bvs85wi1qfb6o1eyrpqv3", StaticFiles(directory="admin_pub"), name="public")
app.mount("/ui",StaticFiles(directory="user_pub"), name="ui")

if __name__ == "__main__":
    bot.init_app(app)
    uvicorn.run(app,port=int(os.environ.get('PORT',8000)))    
    # 启动bot，注意，port端口号要和你的回调地址端口对上