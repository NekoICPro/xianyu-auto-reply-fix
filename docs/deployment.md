# 部署与运行指南

> 返回：[README](../README.md) ｜ 相关：[配置说明](configuration.md) ｜ [常见问题](faq.md)

本页保存 README 中不适合展开的部署细节，README 只保留最短启动路径。

## 环境要求

- **Python**: 3.11+
- **Node.js**: 16+（用于 PyExecJS 执行 JavaScript）
- **系统**: Windows / Linux / macOS
- **架构**: x86_64 (amd64) / ARM64 (aarch64)
- **Docker**: 20.10+（Docker 部署）
- **Docker Compose**: 2.0+（Docker 部署）
- **浏览器依赖**: Playwright Chromium（本地运行需要安装）
- **资源建议**: 建议 2GB+ 内存，预留 10GB+ 存储空间

## 方式一：使用部署脚本（推荐）

### Linux / macOS

```bash
git clone https://github.com/GuDong2003/xianyu-auto-reply-fix.git
cd xianyu-auto-reply-fix
chmod +x docker-deploy.sh
./docker-deploy.sh
```

脚本会自动检查依赖、创建目录、构建镜像并启动服务。

默认访问地址：

- `docker-compose.yml`：`http://localhost:9000`
- `docker-compose-cn.yml`：`http://localhost:8000`

### Windows

```cmd
git clone https://github.com/GuDong2003/xianyu-auto-reply-fix.git
cd xianyu-auto-reply-fix
docker-deploy.bat
```

默认访问地址：

- `docker-compose.yml`：`http://localhost:9000`
- `docker-compose-cn.yml`：`http://localhost:8000`

## 方式二：手动使用 Docker Compose

### 默认配置（已内置大陆优化）

```bash
git clone https://github.com/GuDong2003/xianyu-auto-reply-fix.git
cd xianyu-auto-reply-fix
docker compose up -d
```

访问：`http://localhost:9000`

> 默认使用 1Panel Docker 镜像源 + USTC Debian 源 + 清华 PyPI 源，无需额外配置即可在大陆网络环境下快速构建。

### 国内精简构建配置

使用 `Dockerfile-cn` 构建的精简版镜像（不含 Xvfb/VNC/fluxbox 等虚拟显示组件，适合无头模式运行）：

```bash
git clone https://github.com/GuDong2003/xianyu-auto-reply-fix.git
cd xianyu-auto-reply-fix
docker compose -f docker-compose-cn.yml up -d --build
```

访问：`http://localhost:8000`

## 大陆网络优化说明

本项目所有 Docker 部署文件已默认配置为大陆优化版本，无需额外手动修改镜像源。构建时自动使用以下国内镜像源加速：

| 资源 | 默认源 | 说明 |
| --- | --- | --- |
| Docker 基础镜像 | `docker.1panel.live` | 1Panel Docker 镜像源，加速拉取 `python`、`nginx` 等官方镜像 |
| Debian apt 源 | `mirrors.ustc.edu.cn` | 中科大镜像源，加速系统依赖安装 |
| PyPI 源 | `pypi.tuna.tsinghua.edu.cn` | 清华大学镜像源，加速 Python 依赖安装 |
| Playwright 浏览器下载 | `cdn.npmmirror.com` | npmmirror 镜像源，加速 Chromium 下载 |
| npm 源 | `registry.npmmirror.com` | npmmirror 镜像源，加速 Node.js 包安装 |

### Docker Engine 镜像加速（可选）

除了在 Dockerfile / docker-compose 中使用 1Panel 镜像源外，建议在宿主机配置 Docker Engine 镜像加速器以进一步加速镜像拉取：

```jsonc
// /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.1panel.live"
  ]
}
```

配置后重启 Docker 服务：

```bash
sudo systemctl restart docker
```

### 海外环境构建

如果需要在海外环境构建，可通过构建参数覆盖为官方源：

```bash
docker build --build-arg BASE_IMAGE=python:3.11-slim-bookworm -t xianyu-auto-reply-fix .
```

## 方式三：本地运行

```bash
git clone https://github.com/GuDong2003/xianyu-auto-reply-fix.git
cd xianyu-auto-reply-fix

python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 使用国内 PyPI 镜像源加速安装（大陆推荐）
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用国内镜像加速下载 Playwright 浏览器（大陆推荐）
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright playwright install chromium
# Linux 可能还需要：playwright install-deps chromium

python Start.py
```

访问：`http://localhost:8090`

> 本地运行请确保已安装 Node.js，否则 `PyExecJS` 相关功能无法正常使用。

## 多架构支持

支持的架构：

- `linux/amd64` - Intel / AMD 处理器
- `linux/arm64` - ARM64 处理器

构建方式：

- 提供 `build-multi-arch.sh` 多架构构建脚本
- 支持使用 Docker Buildx 构建 amd64 / arm64 镜像
- Docker 部署和本地运行可在对应架构环境中使用

说明：

- 当前仓库未包含 GitHub Actions 自动构建配置
- 镜像仓库地址请以实际发布情况为准

## 访问地址

部署完成后，您可以通过以下方式访问系统：

| 场景 | Web 管理界面 | API 文档 | 健康检查 |
| --- | --- | --- | --- |
| Docker Compose 默认配置 | `http://localhost:9000` | `http://localhost:9000/docs` | `http://localhost:9000/health` |
| Docker Compose 国内配置 | `http://localhost:8000` | `http://localhost:8000/docs` | `http://localhost:8000/health` |
| 本地运行 | `http://localhost:8090` | `http://localhost:8090/docs` | `http://localhost:8090/health` |

默认管理员账号（首次初始化且未自定义密码时）：

- 用户名：`admin`
- 密码：`admin123`

> ⚠️ 首次登录后请立即修改默认密码。
