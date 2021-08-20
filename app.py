from flask import *
import pymysql
import traceback
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_
from functools import wraps
import random
import qrcode
import base64
from PIL import Image
import io
#区块链
import json
from web3 import Web3, HTTPProvider
from easysolc import Solc #放在文件最上面
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@127.0.0.1:3306/block'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.secret_key = "1"  # str(random.sample('zyxwvutsrqponmlkjihgfedcba',10))
db = SQLAlchemy(app)



#BlockchainInit
w3 = Web3(HTTPProvider("http://localhost:7545"))
w3.eth.defaultAccount = w3.eth.accounts[1]#使用账户0来部署。
solc = Solc()
# 编译智能合约并放在当前目录
solc.compile('./contracts/Election.sol', output_dir='./build')
# 获取智能合约实例 其中abi和bin文件为编译后生成的文件，可以去你的项目目录下找。
my_contract = solc.get_contract_instance(w3=w3, abi_file='./build/Election.abi', bytecode_file='./build/Election.bin')
# 部署智能合约
tx_hash = my_contract.constructor().transact()
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)#等待挖矿过程
# 获得智能合约部署在链上的地址
contractAddr = tx_receipt.contractAddress
with open('./build/Election.abi', 'r') as f:
    abi = json.load(f)
contract = w3.eth.contract(contractAddr, abi=abi)
#创建商品方便查询
#创建商品test
code = contract.functions.createNewCargo("test").call()
contract.functions.createNewCargo("test").transact()
print(code)
res = contract.functions.trancesOf(code).call()
print(res)
# 将商品test转移到第二个账户
contract.functions.transfer(code,w3.eth.accounts[2]).transact()
res = contract.functions.trancesOf(code).call()
print(res)

w3.eth.defaultAccount = w3.eth.accounts[2]
print(w3.eth.accounts[3])
contract.functions.transfer(code,w3.eth.accounts[3]).transact()
res = contract.functions.trancesOf(code).call()
print(res)


############################################
# 数据库
############################################

# 定义ORM
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True)
    organization = db.Column(db.String(80))#所属组织
    flag=db.Column(db.Integer())#0为管理员 9为普通用户
    address = db.Column(db.String(80), unique=True)
    def __repr__(self):
        return '<User %r>' % self.username
# 定义ORM
class food_management(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trace_code = db.Column(db.String(80), unique=True)
    username = db.Column(db.String(80), unique=True)
    address = db.Column(db.String(80), unique=True)
    def __repr__(self):
        return '<User %r>' % self.username

# 创建表格、插入数据
@app.before_first_request
def create_db():
    db.drop_all()  # 每次运行，先删除再创建
    db.create_all()
    admin = User(username='00', password='00', email='admin@example.com',organization="无",flag=0,address=w3.eth.accounts[0])
    db.session.add(admin)

    guestes = [User(username='11', password='11', email='guest1@example.com',organization="开心农村",flag=1,address=w3.eth.accounts[1]),
               User(username='22', password='22', email='guest2@example.com',organization="汪汪加工基地",flag=2,address=w3.eth.accounts[2]),
               User(username='33', password='33', email='guest3@example.com',organization="翻斗大街201",flag=3,address=w3.eth.accounts[3]),
               User(username='44', password='44', email='guest4@example.com',organization="无",flag=9,address=w3.eth.accounts[9])]
    food_add=food_management(trace_code=code,username="33",address=w3.eth.accounts[3])
    db.session.add(food_add)
    db.session.add_all(guestes)
    db.session.commit()


############################################
# 辅助函数、装饰器
############################################

# 登录检验（用户名、密码验证）
def valid_login(username, password):
    user = User.query.filter(and_(User.username == username, User.password == password)).first()
    if user:
        return True
    else:
        return False


# 注册检验（用户名、邮箱验证）
def valid_regist(username, email):
    user = User.query.filter(or_(User.username == username, User.email == email)).first()
    if user:
        return False
    else:
        return True


# 登录验证
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # if g.user:
        if User.query.filter(User.username == session.get('username')).first():
            return func(*args, **kwargs)
        else:
            return redirect(url_for('login_html'))
    return wrapper


@app.route('/')
def index_html():
    return render_template('index.html')

@app.route('/home')
@login_required
def home_html():
    username=session.get('username')
    flag = session.get('flag')
    return render_template('home.html',username=username,flag=flag)

@app.route('/login', methods=['GET', 'POST'])
def login_html():
    error = None
    if request.method == 'POST':
        if valid_login(request.form['username'], request.form['password']):
            username=request.form.get('username')
            session['username'] = username
            session['id'] = User.query.filter(User.username == username).all()[0].id
            session['flag'] = User.query.filter(User.username == username).all()[0].flag
            return redirect(url_for('home_html'))
        else:
            error = '错误的用户名或密码！'

    return render_template('login.html', error=error)


@app.route('/regist', methods=['GET', 'POST'])
def regist_html():
    error = None
    if request.method == 'POST':
        if(not request.form['username'] or not request.form['email']):
            error = '不能为空！'
        elif request.form['password1'] != request.form['password2']:
            error = '两次密码不相同！'
        elif valid_regist(request.form['username'], request.form['email']):
            user = User(username=request.form['username'], password=request.form['password1'],
                        email=request.form['email'],organization="无",flag=9)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login_html'))
        else:
            error = '该用户名或邮箱已被注册！'

    return render_template('regist.html', error=error)

#Permission_Management.html
@app.route('/Permission_Management')
@login_required
def Permission_Management_html():
    username=session.get('username')
    flag = session.get('flag')
    users=User.query.filter().all()
    return render_template('Permission_Management.html',username=username,flag=flag,users=users)

#Permission_Management.html
@app.route('/Permission_Management', methods=[ 'POST'])
@login_required
def submitUser():
    if request.method=="POST" and session.get('flag')==0 :
        if request.form['choice']=='3':
            del_name=request.form['username']
            User.query.filter_by(username=del_name).delete()
            flash("用户："+del_name+"已删除")
            return redirect(url_for('Permission_Management_html'))
        if request.form['choice']=='2':
            old_name=request.form['oldusername']
            change_name = request.form['username']
            change_email = request.form['email']
            change_flag = request.form['flag']
            change_organization = request.form['organization']
            User.query.filter(User.username==old_name).update({"username":change_name,"email":change_email,"flag":change_flag,"organization":change_organization})
            flash("用户：信息已更改")
            return redirect(url_for('Permission_Management_html'))


#add_user.html
@app.route('/add_user')
@login_required
def add_user_html():
    username=session.get('username')
    flag = session.get('flag')
    return render_template('add_user.html',username=username,flag=flag)
#############################################################
#############################################################
#####################上面缺少增加用户模块#####################
#############################################################
#############################################################
#traceability
@app.route('/traceability')
@login_required
def traceability_html():
    username=session.get('username')
    flag = session.get('flag')
    return render_template('traceability.html',username=username,flag=flag)


# traceability.html
@app.route('/traceability', methods=['POST'])
@login_required
def traceability_food():
    if request.method=="POST":
        username = session.get('username')
        flag = session.get('flag')
        try:
            trace_code=int(request.form['trace_code'])
        except:
            flash("请输入正确的数字")
            return redirect(url_for('traceability_html'))
        result = contract.functions.trancesOf(trace_code).call()
        res={}
        if result!=['0x0000000000000000000000000000000000000000']:
            scussse=1
            for i in result:
                res[i]=User.query.filter(User.address == i).all()[0]
        else:
            scussse=0
        return render_template('traceability.html',username=username,flag=flag,scussse=scussse,res=res)



#add_good
@app.route('/add_good')
@login_required
def add_good_html():
    username=session.get('username')
    flag = session.get('flag')
    return render_template('add_good.html',username=username,flag=flag)

#add_good
@app.route('/add_good', methods=['POST'])
@login_required
def add_good():
    if request.method == "POST":
        username=session.get('username')
        flag = session.get('flag')
        foodname=request.form['foodname']
        w3.eth.defaultAccount = w3.eth.accounts[1]
        trace_code = contract.functions.createNewCargo(foodname).call()
        contract.functions.createNewCargo(foodname).transact()
        food = food_management(username= username, address= w3.eth.defaultAccount,trace_code=trace_code)
        db.session.add(food)
        db.session.commit()
        now_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        #生成二维码
        c="{}:{}\n{}:{}\n{}:{}\n{}:{}".format("创建者",username,"创建时间",now_time,"名称",foodname,"溯源码",trace_code)
        img = qrcode.make(c).get_image()
        img.save("D:/" + foodname + ".png")
        imgByteArr = io.BytesIO()
        img.save(imgByteArr, format='PNG')
        imgByteArr = imgByteArr.getvalue()
        img_stream = base64.b64encode(imgByteArr)
        return render_template('add_good.html',username=username,flag=flag,img_stream=bytes.decode(img_stream),trace_code=trace_code)



#transfer_good
@app.route('/transfer_good')
@login_required
def transfer_good_html():
    username=session.get('username')
    flag = session.get('flag')
    return render_template('transfer_good.html',username=username,flag=flag)



#transfer_good
@app.route('/transfer_good', methods=['POST'])
@login_required
def transfer_good():
    if request.method == "POST":
        username=session.get('username')
        flag = session.get('flag')
        trace_code=request.form['trace_code']
        food_to = request.form['food_to']
        try:
            from_id = User.query.filter(User.username == username).all()[0].id-1
            to_id=User.query.filter(User.username == food_to).all()[0].id-1
            from_name=username
            to_name = User.query.filter(User.username == food_to).all()[0].username
            w3.eth.defaultAccount = w3.eth.accounts[from_id]
            contract.functions.transfer(int(trace_code), w3.eth.accounts[to_id]).transact()
            food_management.query.filter(food_management.username == from_name).update(
                {"username": to_name, "address": w3.eth.accounts[to_id]})
            flash("转移成功")
        except:
            flash("转移失败")
        return render_template('transfer_good.html',username=username,flag=flag)



#now_food
@app.route('/now_food')
@login_required
def now_food_html():
    username=session.get('username')
    flag = session.get('flag')
    res=[]
    for i in food_management.query.filter(food_management.username == username).all():
        res.append(i.trace_code)
    return render_template('now_food.html',username=username,flag=flag,res=res)




if __name__ == '__main__':
    app.run(debug=True)