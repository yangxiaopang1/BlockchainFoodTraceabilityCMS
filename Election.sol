pragma solidity ^0.5.0;


contract Election{
    string public constant name="food_trac";
    string public constant symbol="";
    //商品数量
    uint256 public _capacity=0;
    //管理员地址
    // address private _founder;
    
    
    //权限状态位 用户创建商品 用户持有商品 用户交易记录数据
    // mapping(address => uint8) public _authorization;
    mapping(uint256 => string) public _cargoesName;
    mapping(address => mapping(uint256 => uint256)) public _cargoes;
    mapping(address => uint256) public _cargoesCount;
    mapping(address => mapping(uint256 => uint256)) public _holdCargoes;
    mapping(uint256 => uint256) public _holdCargoIndex;
    mapping(address => uint256) public _holdCargoesCount;
    mapping(uint256 => mapping(uint256 => Log)) public _logs;
    mapping(uint256 => uint256) public _transferTimes;
    
    //相应事件
    event NewCargo(address indexed _creater, uint256 _cargoID);
    event Transfer(uint256 indexed _cargoID, address indexed _from, address _to);
    event Authorize(address indexed _address, bool _state);
    
    //日志结构体
    struct Log{
        uint256 time;
        address holder;
    }
    mapping(uint => productnew) public productnews;//商品索引
    
    //
    struct productnew{
        uint id;
        uint num;//商品序号  溯源码
        uint createTime;//创建时间
        address nowhold;//当前持有者地址
        address createMan;//创建者地址
        string cargoName;//名称
        uint TranTIME;//转移时间
        address befhold;//前一个持有者地址
    }
    
    // 构造函数，合约创建时候调用
    constructor () public{
        _founder = msg.sender;
        // _authorization[msg.sender] = 2;
    }
    
    //商品数量
    function capacity() public view returns(uint256){return _capacity;}
    //当前地址下商品数
    function capacityOf(address _owner) public view returns(uint256){return _cargoesCount[_owner];}
    //ID查询商品名称
    function cargoNameOf(uint256 _cagoID)public view returns(string memory){return _cargoesName[_cagoID];}
    //查询该账户权限
    // function permissionOf(address _user)public view returns(uint8){return _authorization[_user];}
    //根据商品ID查询商品流转次数
    function transferTimesOf(uint256 _cagoID) public view returns(uint256){return _transferTimes[_cagoID];}
    
    
    //当前商品ID持有者地址
    function holderOf(uint256 _cargoID) public view returns(address){
        return _logs[_cargoID][_transferTimes[_cargoID]].holder;
    }
    
    //该商品ID转移记录，返回持有时间与账户地址
    function trancesOf(uint256 _cargoID) public view returns(address[] memory holders){
        uint256 transferTime = _transferTimes[_cargoID];
        holders = new address[](transferTime+1);
        uint256[] memory times;
        times= new uint256[](transferTime+1);
        for(uint256 i=0;i<=transferTime;i++){
            Log memory log=_logs[_cargoID][i];
            holders[i]=log.holder;
            times[i]=log.time;
        }
        return holders;
    }
     
    //当前该地址创建的商品（包括以及转移走的）
    function allCreated() public view returns(uint256[] memory cargoes){
        address _creater=msg.sender;
        uint256 count = _cargoesCount[_creater];
        cargoes = new uint256[](count);
        for(uint256 i=0;i<count;i++){
            cargoes[i]=_cargoes[_creater][i];
        }
    }
    
    
    //当前地址持有商品
    function allHolding(address _owner) public view returns(uint256[] memory cargoes){
        uint256 count = _holdCargoesCount[_owner];
        for(uint256 i=0;i<count;i++){
            cargoes[i]=_holdCargoes[_owner][i];
        }
    }
    
    //新货物创建  输入货物名字 返回商品创建好的ID
    function createNewCargo(string memory _cargoName)public returns(uint256 cargoID){
        // uint8 authorization =_authorization[msg.sender];
        //require(authorization>1,"mei shou quan");
        uint256 count=_cargoesCount[msg.sender];
        // require(count+1>count,"da dao shang xian");
        // require(_capacity+1>_capacity,"da dao shang xian");
        
        //生成唯一商品ID
        cargoID=uint(keccak256(abi.encodePacked(msg.sender,count,_capacity)))%100000000000;
        _cargoes[msg.sender][count]=cargoID;
        //商品名称存储
        _cargoesName[cargoID]=_cargoName;
        //返回创建商品日志
        _logs[cargoID][0]=Log({
            time:block.timestamp,
            holder:msg.sender
        });
        _addToHolder(msg.sender,cargoID);
        // emit NewCargo(msg.sender,cargoID);
        _cargoesCount[msg.sender]++;
        _capacity++;
        
        //创建商品，并赋予索引
        productnews[_capacity]=productnew(_capacity,cargoID,now,msg.sender,msg.sender,_cargoName,0,msg.sender);
    }
    
    //设置权限
    // function serPermission(address _address,bool _state)public{
    //     if(_state){
    //         _authorization[_address]=1;
    //     }else{
    //         _authorization[_address]=0;
    //     }
    //     emit Authorize(_address,_state);
    // }
    
    //转移商品。由商品持有者调用
    function transfer(uint256 _cargoID,address _to)public returns(bool success){
        uint256 transferTime = _transferTimes[_cargoID];
        address holder = _logs[_cargoID][transferTime].holder;
        //商品持有者不为零地址
        require(holder != address(0),"Nonexistent cargo");
        //商品拥有者必须是交易发送者
        require(holder == msg.sender , "Unauthorized");
        //目标地址不为交易发送者
        require(holder != _to,"Don't allow transfer to yourself");
        //目的地址不为零地址
        require(_to !=address(0),"Invalid target address");
        
        //商品转移记录增加
        _transferTimes[_cargoID]++;
        _logs[_cargoID][transferTime+1]=Log({
            time:block.timestamp,
            holder:_to
        });
        
        //将其移动给目标用户
        _removeFromHolder(msg.sender,_cargoID);
        _addToHolder(_to,_cargoID);
        emit Transfer(_cargoID,holder,_to);
        
        //新建转移商品方法
        uint littleID=0;
        for(uint i=0;i<=_capacity;i++){
            productnew storage productTemp = productnews[i];
            if(productTemp.num==_cargoID){
                littleID=i;
            }
        }
        require(littleID!=0);
        productnew storage productnewa=productnews[littleID];
        productnewa.befhold=productnewa.nowhold;//前一个持有者
        productnewa.nowhold=_to;
        productnewa.TranTIME=now;
        return true;
    }
    
    //将_corgoID商品从原持有者移除
    function _removeFromHolder(address _oriHolder,uint256 _cargoID) private{
        uint256 count=_holdCargoesCount[_oriHolder];
        uint256 index=_holdCargoIndex[_cargoID];
        _holdCargoes[_oriHolder][index]=_holdCargoes[_oriHolder][count];
        _holdCargoesCount[_oriHolder]--;
    }
    
    //将_corgoID商品转移给新地址
    function _addToHolder(address _newHolder, uint256 _cargoID) private{
        uint256 count=_holdCargoesCount[_newHolder];
        _holdCargoIndex[_cargoID]=count+1;
        _holdCargoes[_newHolder][count+1]=_cargoID;
        _holdCargoesCount[_newHolder]++;
    }
}