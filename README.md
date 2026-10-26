# 观境：欧瑞博 VM1 玄关信息屏

这是为 **Android 5.x / Via 浏览器 / 低内存** 设计的轻量静态网页。

## 主要功能

- 北京时间、日期、星期。
- 成都市当前天气、体感、湿度、风速、阵风。
- 今日逐小时温度和降雨概率、未来16天温度/降雨概率/风速及阵风。
- 国际时政4条、全球财经3条、成都本地3条；来自Google新闻RSS聚合，过滤部分娱乐词，不是正式平台热搜排名。
- 国际现货黄金 XAU/USD（美元/金衡盎司；并非中国金店回购价）。
- 四川及周边USGS近7天震情**速报**，不是地震预警。
- 官方气象预警/灾害信息查询快捷入口；**默认未接入官方实时预警**。

## 最容易的预览方法

直接打开 `index.html?demo=1`，即可看设计和布局。**所有新闻和天气都是设计占位示例，页面会显著显示预览提示。**

打开默认 `index.html` 时，如果 `data/dashboard.json` 尚未生成，新闻、黄金等将显示未接入；天气会尝试直连Open-Meteo，但安卓5旧版浏览器的TLS/跨域兼容性不保证。

## 长期使用（GitHub Pages）：电脑操作 5 步

1. 将完整 ZIP 下载到电脑并**解压**，得到 `index.html`、`data`、`scripts`、`.github` 等内容。
2. 在 GitHub 创建一个新的 **Public**（公开）仓库，例如 `vm1-dashboard`，勾选“Add a README file”，点击 Create repository。这样不会影响已经存在的 T 表格项目。
3. 进入新仓库，点击 **Add file → Upload files**，把解压目录里面的文件和文件夹（特别是整个 `.github`、`data`、`scripts`）拖入上传区，选择 **Commit directly to main**，提交。注意：**ZIP本身不能直接当网站上传**，上传的目录根层必须有 `index.html`，不是外面再包一层文件夹。如果 GitHub 网页上传没保留文件夹内的文件，须单独检查、补齐。
4. 在仓库 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**（注意：**不是**“Deploy from a branch”）。
5. 打开仓库 **Actions → 更新并发布 VM1 玄关信息屏 → Run workflow**，选 `main` 运行一次。等到运行显示绿色成功图标，再返回 **Settings → Pages** 查看网页地址。预计形如 `https://你的用户名.github.io/vm1-dashboard/`。网页访问成功后，把这个地址设置成魔镜 Via 浏览器主页。

项目同时执行后台更新和网站发布：每半小时**尝试**拉取新数据并重新发布网页。GitHub 定时任务可能延迟，页面每10分钟重新读取JSON缓存；因此不承诺实时秒级新闻或气象预警。新闻主要来自Google News RSS，在GitHub Actions机房有可能被拒绝；若某一来源失败，页面会显示真实更新时间或数据不可用。

GitHub Actions工作流需要对仓库内容有写权限：如果 `git push` 显示403，进入 `Settings → Actions → General → Workflow permissions`，选择 `Read and write permissions` 并保存，再次运行工作流。若GitHub Pages无法访问，检查Pages设置是否为 `GitHub Actions`，以及Actions是否显示成功。**网页与发布的数据均可公开访问，不要上传隐私信息。**

### 如何滑动

VM1横屏时：手指在网页普通区域**向上划**可往下看资讯，在网页普通区域向下划可返回顶部；在「未来16天天气趋势」卡片里**左右划**查看后面的日期。没有固定整屏锁定，不必额外装翻页软件。无法上下滑时，请关闭 Via 的阅读/桌面滚动限制，并检查是否存在屏幕触摸故障。

## 灾害预警的边界

**本网站不能用作生命安全预警终端。** 预警栏默认提示“官方实时预警尚未接入，状态未知”，不能将未获取数据说成“当前没有预警”。

`data/official_alerts.json` 是可选的人工公告配置，只应填入已核实的官方公告，必须包含 `title`, `publisher`, `source_url`, `expires_at`；可选 `level`, `area`, `published_at`。空数组 `[]` 表示**未接入**，不是“安全”。网页会检查过期时间。

USGS近7天地震记录通常是**地震发生之后**才公开，绝非提前数秒预警。请继续使用微信“中国地震台网”或“四川地震台”官方预警服务，以及手机系统的应急警报。网站不承诺任何震前通知。

天气预报来自Open-Meteo的数值模型，尤其第8—16天不应当成确定性预报；真实预警级别以中国气象主管部门发布为准。

## 技术与可扩展性

- 单个HTML（CSS、JS一体，无构建依赖）
- 纯JavaScript ES5 + XMLHttpRequest（避免依赖旧WebView不支持的fetch、React等）
- Python标准库后台拉取数据，无需pip安装第三方模块
- 数据结构统一保存在 `data/dashboard.json`：后续房价、黄金人民币报价、家电控制可增添模块
- 预计VM1小屏上可滚动浏览，禁止高清视频等重内容
- 如果设备网络不能访问GitHub Pages或Google新闻，后台部署地区与访问线路需要另行调整；不要承诺一定可用。

### 数据来源

- Open-Meteo `https://open-meteo.com/` (非商业使用需遵守其授权条款)
- Google News RSS `https://news.google.com/rss/`（新闻标题和跳转，尊重原文版权）
- 英文后备源 BBC RSS `https://feeds.bbci.co.uk/news/`
- Gold API `https://gold-api.com/`（国际现货美元计价）
- USGS `https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php`
- 国家应急广播 `https://www.cneb.gov.cn/`
- 四川省地震局 `https://www.scdzj.gov.cn/`
