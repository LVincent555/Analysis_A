# RES-036 frontend-client 服务器公钥 Electron 目录包重打结果

## 状态

[SOLVED]

## 背景

本地上一版 `frontend-client` Electron 目录包是在缺少 `frontend-client/.env` 的情况下构建的，React 产物实际使用默认开发公钥：

- `login-rsa-dev-2026-07`

服务器当前后端与前端安全登录配置已切换到同一组正式登录公钥：

- `REACT_APP_SECURE_LOGIN_KEY_ID=login-rsa-local-001`
- `REACT_APP_SECURE_LOGIN_PUBLIC_KEY_FINGERPRINT=tHYTbLsGfav18UklGgUStsPsa99DKRllYeBu9CTV4sg`

因此旧包不能作为当前服务器安全登录配置下的有效客户端包。

## 执行动作

1. 通过本机 SSH 别名 `analysis-a-codex` 连接 dev 服务器。
2. 定位服务器项目目录为 `/root/DA/Analysis_A`。
3. 从服务器拉取 `/root/DA/Analysis_A/frontend-client/.env` 到本地 `frontend-client/.env`。
4. 删除本地旧构建产物：
   - `frontend-client/build`
   - `frontend-client/dist/win-unpacked`
   - `frontend-client/dist/StockAnalysis-0.6.2-win-unpacked-20260709.zip`
5. 使用服务器前端 `.env` 重新执行 React production build。
6. 使用 `GENERATE_SOURCEMAP=false` 重新构建，避免 source map 内继续携带源码默认 dev key 字符串。
7. 执行 Electron 目录包构建并产出 `dist/win-unpacked`。
8. 压缩生成新版可执行目录包 zip。

## 产物

新版 zip：

- `frontend-client/dist/StockAnalysis-0.7.0-win-unpacked-server-key-20260709.zip`

包大小：

- `148,205,778` bytes

SHA256：

- `B8040BB0B44E204F14F7ED783474AC441C7F2D33CCA9DFF92817A66E0840DE40`

运行入口：

- 解压 zip 后运行 `StockAnalysis.exe`

## 验证结果

React build 产物验证：

- 命中 `login-rsa-local-001`
- 命中 `tHYTbLsGfav18UklGgUStsPsa99DKRllYeBu9CTV4sg`
- 未命中 `login-rsa-dev-2026-07`

Electron `win-unpacked/resources/app.asar` 验证：

- 命中 `login-rsa-local-001`
- 命中 `tHYTbLsGfav18UklGgUStsPsa99DKRllYeBu9CTV4sg`
- 未命中 `login-rsa-dev-2026-07`

zip 结构验证：

- zip 内包含 `StockAnalysis.exe`

## 注意事项

1. 本次交付为 `win-unpacked` 目录包压缩版，不是 NSIS 安装器。
2. `electron-builder --win --dir` 在本机仍会尝试下载并解压 `winCodeSign`，最终因 Windows 当前权限无法创建符号链接而报错；但该报错发生在目录包生成之后，`dist/win-unpacked` 已完整产出并完成 key 验证。
3. 若后续需要正式安装器，应在开启 Windows Developer Mode 或管理员/具备符号链接权限的环境中重新执行 NSIS 打包。
4. `frontend-client/.env` 为从服务器同步的前端公钥配置，应继续保持不提交到 Git。
