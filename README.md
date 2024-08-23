# 麻雀一番街MAX
模仿[雀魂MAX](https://github.com/Avenshy/MajsoulMax)的麻雀一番街全解锁工具。
目前支持解锁：角色，皮肤，桌布，麻将牌，BGM，特效等。

目前仍处于开发阶段，可能会有各种不稳定因素，使用前请做好心理准备。

接下来准备继续完善一下细节，另外有考虑添加基于[Akagi](https://github.com/shinkuan/Akagi)的AI功能。

# 使用方法

> 请注意：此类工具可能存在封号的风险，本人对使用此工具产生的任何后果概不负责。使用此工具即代表您同意此点。

> 另外，本工具仅供学习交流使用，严禁用于商业用途。下载后请于24小时内删除。

由于工具目前并不稳定，暂不提供windows可执行文件，因此请自行安装相关环境。

使用方法基本可以照搬[雀魂MAX](https://github.com/Avenshy/MajsoulMax?tab=readme-ov-file#%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E)

另外对于Linux用户，由于一番街没有网页版，而Linux下也没有类似Proxifier的代理工具。因此可以参考mitmproxy的[相关文档](https://docs.mitmproxy.org/stable/howto-transparent/)设置透明代理，具体代码片段参考如下：
```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv4.conf.all.send_redirects=0

sudo iptables -t nat -A OUTPUT -d 3.115.226.82 -p tcp -m owner ! --uid-owner test --dport 80 -j REDIRECT --to-port 8082
sudo iptables -t nat -A OUTPUT -d 3.115.226.82 -p tcp -m owner ! --uid-owner test --dport 443 -j REDIRECT --to-port 8082

sudo useradd test -m -s/bin/bash
setfacl -m "u:test:rwx" <path/to/project>

cd <path/to/project> && sudo -u test mitmdump -p 8082 -s addons.py --mode transparent --showhost --set block_global=false --ssl-insecure
```
其中新用户名我取为test，端口为8082，这两个可自行更改。
由于涉及系统层面的修改，运行之前请明确自己知道自己在做什么。

# 目前的一些小问题
打开背包时间过长，且第一次装备装备可能需要等待很长时间，因此若点击没反应请不要重复点击。（没找到返回所有装备信息的API，只能遍历所有ID，因此会添加很多无效的ID，导致客户端处理缓慢。所有装备的ID信息似乎是存在本地？可能解包一下会有收获？TODO）
