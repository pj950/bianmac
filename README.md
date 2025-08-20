# bianmac

# 币安趋势反转检测与微信提醒系统

## 系统功能

✅ **自动检测趋势反转信号**
- 多种技术指标综合分析（RSI、MACD、布林带、移动平均线等）
- 智能信号强度评分
- 支持自定义检测参数

✅ **智能通知逻辑** 
- 买入信号：仅对观察列表中且未持仓的币种发送
- 卖出信号：仅对持仓列表中的币种发送
- 避免重复无效通知

✅ **多种通知方式**
- 企业微信推送
- Server酱微信通知
- 邮件通知备用

## 安装步骤

### 1. 安装Python依赖

```bash
pip install requests pandas numpy ta logging smtplib email datetime
```

### 2. 下载代码文件

将以下文件保存到同一目录：
- `binance_trend_detector.py` - 主程序
- `wechat_notifier.py` - 微信通知模块
- `trading_config.json` - 配置文件

### 3. 配置文件设置

编辑 `trading_config.json`：

```json
{
  "holding_list": [
    "BTCUSDT",
    "ETHUSDT",
    "ADAUSDT"
  ],
  "watch_list": [
    "BTCUSDT",
    "ETHUSDT", 
    "ADAUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "SOLUSDT"
  ],
  "notification_settings": {
    "min_signal_strength": 4,
    "check_interval": 300,
    "rsi_oversold": 30,
    "rsi_overbought": 70
  },
  "wechat_config": {
    "corp_id": "你的企业ID",
    "corp_secret": "你的应用密钥", 
    "agent_id": "应用ID",
    "to_user": "@all"
  }
}
```

## 微信通知配置

### 方法一：企业微信（推荐）

1. **注册企业微信**
   - 访问 https://work.weixin.qq.com/
   - 注册企业微信账号

2. **创建应用**
   - 进入管理后台 → 应用管理 → 自建
   - 创建应用，获取 `AgentId` 和 `Secret`

3. **获取企业ID**
   - 我的企业 → 企业信息 → 企业ID

4. **配置参数**
   ```json
   "wechat_config": {
     "corp_id": "ww1234567890abcdef",
     "corp_secret": "your_app_secret_here", 
     "agent_id": "1000002",
     "to_user": "@all"
   }
   ```

### 方法二：Server酱

1. **获取SCKEY**
   - 访问 https://sct.ftqq.com/
   - 微信登录获取SCKEY

2. **配置参数**
   ```json
   "wechat_config": {
     "server_chan_key": "SCT123456789abcdef"
   }
   ```

## 使用方法

### 启动监控

```bash
python binance_trend_detector.py
```

### 运行选项

**1. 单次检测**
- 对所有配置的交易对进行一次性检测
- 立即显示结果并发送符合条件的信号

**2. 持续监控** 
- 按设定间隔持续监控
- 默认5分钟检测一次
- 自动发送通知

### 信号触发条件

**买入信号触发条件：**
- 币种在观察列表中
- 币种不在持仓列表中
- 满足至少2个技术指标买入条件
- 信号强度≥4分

**卖出信号触发条件：**
- 币种在持仓列表中
- 满足至少2个技术指标卖出条件  
- 信号强度≥4分

## 技术指标说明

### 主要指标

1. **RSI (相对强弱指数)**
   - 超卖区(<30)反弹 → 买入信号
   - 超买区(>70)回落 → 卖出信号

2. **移动平均线交叉**
   - 短期线上穿长期线 → 买入信号(金叉)
   - 短期线下穿长期线 → 卖出信号(死叉)

3. **MACD指标**
   - MACD线上穿信号线 → 买入信号
   - MACD线下穿信号线 → 卖出信号

4. **布林带**
   - 价格触及下轨 → 买入信号
   - 价格触及上轨 → 卖出信号

5. **成交量确认**
   - 放量突破增强信号可靠性

### 信号强度评分

- **1-3分**: 弱信号，建议观望
- **4-6分**: 中等信号，可以考虑
- **7-10分**: 强信号，重点关注

## 自定义配置

### 修改检测参数

```python
# 在主程序中修改
self.rsi_period = 14          # RSI周期
self.ma_short = 9             # 短期均线
self.ma_long = 21             # 长期均线
self.volume_ma_period = 20    # 成交量均线
```

### 调整信号阈值

```json
"notification_settings": {
  "min_signal_strength": 4,    // 最低信号强度
  "check_interval": 300,       // 检测间隔(秒)
  "rsi_oversold": 30,         // RSI超卖线
  "rsi_overbought": 70        // RSI超买线
}
```

## 注意事项

⚠️ **风险提示**
- 本系统仅供参考，不构成投资建议
- 交易有风险，请理性投资
- 建议结合其他分析方法使用

⚠️ **使用建议**
- 定期更新持仓列表和观察列表
- 根据市场情况调整参数
- 关注信号强度，优先关注高强度信号

⚠️ **技术限制**
- 需要稳定的网络连接
- 币安API有调用频率限制
- 微信通知可能有延迟

## 故障排除

### 常见问题

1. **无法获取数据**
   - 检查网络连接
   - 确认币安API可访问

2. **微信通知失败**
   - 检查企业微信配置
   - 确认应用权限设置

3. **信号不准确**
   - 调整技术指标参数
   - 增加信号强度阈值

### 日志查看

程序运行时会输出详细日志：
```
2025-08-20 10:30:00 - INFO - 开始检测 5 个交易对
2025-08-20 10:30:01 - INFO - BTCUSDT: BUY (强度: 7)
2025-08-20 10:30:01 - INFO - 已发送BTCUSDT的BUY信号通知
```

## 进阶功能

### 1. 添加新的技术指标

可以在 `calculate_technical_indicators` 方法中添加更多指标：

```python
# 威廉指标
df['williams_r'] = ta.momentum.WilliamsRIndicator(
    df['high'], df['low'], df['close']).williams_r()

# CCI指标  
df['cci'] = ta.trend.CCIIndicator(
    df['high'], df['low'], df['close']).cci()
```

### 2. 自定义信号逻辑

在 `detect_trend_reversal` 方法中添加自定义判断逻辑：

```python
# 自定义条件
if custom_condition:
    buy_signals.append("自定义买入条件")
    signal_strength += 2
```

### 3. 数据持久化

可以添加数据库支持，存储历史信号和性能统计。

## 更新日志

- **v1.0**: 基础版本，支持主要技术指标
- **v1.1**: 添加微信通知功能
- **v1.2**: 优化信号强度算法
- **v1.3**: 增加配置文件支持

## 技术支持

如需帮助或有建议，可以：
1. 查看程序日志了解运行状态
2. 调整配置参数优化效果
3. 根据实际需求修改代码逻辑

---

**免责声明**: 本系统仅用于技术分析和学习目的，所有交易决策请自行承担风险。
