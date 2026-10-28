# RDK X5 网络 IP 与 SSH 配置文档

## 一、RDK X5 网络 IP 配置

### 1. N505 WiFi

- **WiFi 名称：** `Bad_puppy` / `Bad_Puppy_5G`
- **RDK X5 IP：** `192.168.31.238`

### 2. SZU_WLAN WiFi

- **WiFi 名称：** `SZU_WLAN`
- **RDK X5 IP：** `暂无`

### 3. Visincept WiFi

- **WiFi 名称：** `Visincept-Office`
- **RDK X5 IP：** `172.16.6.16`

---

## 二、RDK X5 SSH 免密登录配置

通过 SSH 密钥认证，实现 Windows 电脑免密连接 RDK X5，方便使用 VS Code 远程开发。

### 1. 生成 SSH 密钥

在 Windows PowerShell 中执行：

```powershell
ssh-keygen -t ed25519
```

按提示操作，使用默认路径保存密钥。如果已有同名密钥，不要覆盖，可以直接使用。

### 2. 将公钥上传到 RDK X5

在 Windows PowerShell 中执行：

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh sunrise@192.168.31.238 "mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys; chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys"
```

将 `192.168.31.238` 替换为 RDK X5 当前的实际 IP 地址，输入一次开发板密码即可。

### 3. 配置 SSH 连接

打开 Windows SSH 配置文件：

```powershell
notepad "$env:USERPROFILE\.ssh\config"
```

添加以下配置：

```sshconfig
Host rdk-x5
    HostName 192.168.31.238
    User sunrise
    IdentityFile ~/.ssh/id_ed25519
```

其中 `HostName` 需要修改为 RDK X5 的实际 IP 地址。

### 4. 测试 SSH 连接

在 Windows PowerShell 中执行：

```powershell
ssh rdk-x5
```

如果无需输入开发板登录密码即可连接，说明 SSH 免密登录配置成功。
