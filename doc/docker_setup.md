
# 需要配置 Docker 镜像加速器。执行以下步骤：

## 配置 Docker 镜像加速器
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF

## 重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

