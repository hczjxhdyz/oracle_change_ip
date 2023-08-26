### 简介
通过PING检测Oracle被墙IP自动更换并且更新Cloudflare DNS记录

### 该程序主要通过以下方式实现：

1. 通过 Oracle Cloud Infrastructure API 获取当前正在运行的实例列表；
2. 对于每个运行中的实例，获取其 VNIC 列表，进而获取每个 VNIC 的 ID；
3. 通过 VNIC ID 获取对应的 Public IP ID 和 Private IP ID；
4. 通过 Public IP ID 获取 Public IP 地址；
5. 检测 Public IP 地址是否可用；
6. 如果 Public IP 地址不可用，则重新创建 Public IP，并更新对应的 DNS 解析记录。

### 环境要求
- python3
- Oci包

### 安装
1. 安装Python3
> 自行网上搜索教程安装
2. 安装OCI依赖包
```
pip3 install oci
```
### Docker 安装
1. 克隆仓库  
```
git clone https://github.com/hczjxhdyz/oracle_change_ip.git 
cd oracle_change_ip
```
2. 复制修改配置文件
```
cp ./config/config_template.json ./config/config.json
```
然后打开./config/config.json 修改内容，  
填写oci配置、ocid跟域名的对对照表、cf配置

此配置是在申请 OCI 时自动生成的，具体申请过程请参考：https://github.com/877007021/oracle-cloud-network-tools

| 配置        | 描述                                                         | 必须 |
| ----------- | ------------------------------------------------------------ | ---- |
| user        |                                                              | 是   |
| fingerprint |                                                              | 是   |
| tenancy     |                                                              | 是   |
| region      |                                                              | 是   |
| key_file    | 申请 OCI 时下载的 pem 文件，项目默认使用 oci.pem，如果名称不一致请更改 | 是   |


cloudflare 的配置信息，用于更改 cloudflare 的 DNS 解析记录

| 配置               | 描述           | 必须 |
| ------------------ | -------------- | ---- |
| cloudflare_api_token | api_token        | 是   |
| zone            | 需要更新的域名 | 是   |