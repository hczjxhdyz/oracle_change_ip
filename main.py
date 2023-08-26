import oci
import requests
import subprocess
import time
import datetime
import sys
import json

# 获取配置信息
with open('./config/config.json', "r") as json_file:
    accounts = json.load(json_file)

cloudflare_api_url = "https://api.cloudflare.com/client/v4/"
# 更新dns解析
def update_cloudflare_dns(record_name, ip_address, api_token, cloudflare_zone_name):
    # # 获取区域ID
    # headers = {'X-Auth-Key': cloudflare_api_key, 'X-Auth-Email': cloud_email} # 请求头
    headers = {'Authorization': "Bearer " + api_token}
    response = requests.get(cloudflare_api_url + 'zones?name=' + cloudflare_zone_name, headers=headers)
    zid = response.json()['result'][0]['id']

    # 获取记录ID
    response = requests.get(cloudflare_api_url + 'zones/' + zid + '/dns_records?name=' + record_name, headers=headers)
    rid = response.json()['result'][0]['id']

    # 更新记录
    data = {
        "type": "A",
        "name": record_name,
        "content": ip_address,
        "ttl": 1,
        "proxied": False
    }
    response = requests.put(cloudflare_api_url + 'zones/' + zid + '/dns_records/' + rid, headers=headers, json=data)


# 修改IP地址
def change_ip_address(public_ip_id, virtual_network_client, tenancy):
    # 获取public 信息 get_public_ip_by_ip_address
    info = virtual_network_client.get_public_ip_by_ip_address(
        get_public_ip_by_ip_address_details=oci.core.models.GetPublicIpByIpAddressDetails(
            ip_address=public_ip_id)).data
    # 获取public_ip_id 和 private_ip_id
    public_ip_id = info.id 
    private_ip_id = info.private_ip_id 
    # 删除IP
    virtual_network_client.delete_public_ip(public_ip_id)
    # 获取新的IP
    new_ip_info = virtual_network_client.create_public_ip(
    create_public_ip_details=oci.core.models.CreatePublicIpDetails(
        compartment_id=tenancy,
        lifetime="EPHEMERAL",
        private_ip_id=private_ip_id)).data
    return new_ip_info.ip_address

# 检测IP是否被墙
def checkIp(ip_address):
    ping_command = ["ping", "-c" , "10", ip_address]
    failed_count = 0
    try:
        output = subprocess.check_output(ping_command)
    except subprocess.CalledProcessError as e:
        # 当 ping 命令出现异常时，输出异常信息并返回 False
        print(e.output.decode())
        return False

    # 解析 ping 命令的输出，并统计失败次数
    for line in output.decode().split("\n"):
        if "icmp_seq" in line and "time=" not in line:
            failed_count += 1

    # 如果失败次数等于 10，则说明 IP 不可达
    if failed_count == 10:
        return False
    else:
        return True

# 输出日志
def log_info(msg):
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    print("[" + formatted_time + "] " + msg, flush=True) # 输出到控制台
    with open("./config/log.txt","a") as file:   #输出到log文件
        print("[" + formatted_time + "] " + msg, file=file)

# 封装检测操作
def check_main():
    # 轮询账号列配置
    for account in accounts:
        config = oci.config.validate_config(account['config'])
        config = account['config']
        # 初始化 OCI 客户端
        compute_client = oci.core.ComputeClient(config)
        virtual_network_client = oci.core.VirtualNetworkClient(config)
        vnic_to_domain = account['mapping']
        # 获取实例列表
        instances = compute_client.list_instances(config['tenancy']).data

        for instance in instances:
            instance_id = instance.id
            power = instance.lifecycle_state #机器运行状况
            if power != "RUNNING": continue #如果机器不在运行状态则跳过下面的操作
            # 服务器VNIC列表
            vnics = compute_client.list_vnic_attachments(compartment_id=config["tenancy"] ,instance_id=instance_id).data
            for vnic in vnics:
                vnic_id = vnic.vnic_id
                vnic_info = virtual_network_client.get_vnic(vnic_id).data
                public_ip = vnic_info.public_ip
                domain = vnic_to_domain.get(vnic_id)    #获取域名对照表
                if domain is None:
                    print("域名对照表中无此网卡信息，跳过处理")
                    continue
                # 开始检测IP是否被墙
                log_info("正在检测IP：" + public_ip)
                if(checkIp(public_ip) == True): 
                    print("IP:" + public_ip + " 检测正常")
                    continue
                log_info("节点:" + domain + " IP:" + public_ip + " 被墙，执行更换IP操作")
                # 更换IP
                new_public_ip = change_ip_address(public_ip, virtual_network_client, config["tenancy"])
                log_info("更换IP成功,新的IP为："+ new_public_ip)
                # 更新DNS解析
                update_cloudflare_dns(domain,new_public_ip, account['cloudflare']['cloudflare_api_token'], account['cloudflare']['zone'])

# 根据value从字典中查找key
def find_ocid(vnic_to_domain, domain):
    for region in vnic_to_domain:
        for vnic, d in region['mapping'].items():
            if d == domain:
                return vnic,region['config'],region
    return None,None

def main():
    args = sys.argv
    # 如果存在参数则执行手动换IP操作
    if(len(args) >=2):
        domain = args[1]
        vnic_id, configfile , account= find_ocid(accounts, domain)
        if (vnic_id == None) :
            print("字典中未找到你输入的域名")
        else:
            # 初始化 OCI 客户端
            config = oci.config.validate_config(configfile)
            config = configfile
            virtual_network_client = oci.core.VirtualNetworkClient(config)
            vnic_info = virtual_network_client.get_vnic(vnic_id).data
            public_ip = vnic_info.public_ip
            # 更换IP
            new_public_ip = change_ip_address(public_ip, virtual_network_client, config["tenancy"])
            log_info("更换IP成功,新的IP为：" + new_public_ip)
            # 更新DNS解析
            update_cloudflare_dns(domain,new_public_ip, account['cloudflare']['cloudflare_api_token'], account['cloudflare']['zone'])
            log_info("DNS更新成功")
        
    else:
        while True:
            check_main()
            time.sleep(30)

if __name__ == '__main__':
    main()
