import requests
import json
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class WeChatNotifier:
    """微信通知类 - 支持企业微信和Server酱"""
    
    def __init__(self, config: dict):
        self.config = config
        self.access_token = None
        self.token_expires_at = 0
    
    def get_access_token(self) -> str:
        """获取企业微信访问令牌"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        try:
            url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            params = {
                'corpid': self.config.get('corp_id'),
                'corpsecret': self.config.get('corp_secret')
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get('errcode') == 0:
                self.access_token = data['access_token']
                self.token_expires_at = time.time() + data['expires_in'] - 60
                return self.access_token
            else:
                logger.error(f"获取access_token失败: {data}")
                return None
                
        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
            return None
    
    def send_wechat_work_message(self, title: str, content: str) -> bool:
        """发送企业微信消息"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            message_data = {
                "touser": self.config.get('to_user', '@all'),
                "msgtype": "text",
                "agentid": self.config.get('agent_id'),
                "text": {
                    "content": f"{title}\n\n{content}"
                },
                "safe": 0
            }
            
            response = requests.post(url, json=message_data)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info("企业微信消息发送成功")
                return True
            else:
                logger.error(f"企业微信消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"发送企业微信消息异常: {e}")
            return False
    
    def send_server_chan_message(self, title: str, content: str, sckey: str) -> bool:
        """通过Server酱发送微信消息"""
        try:
            url = f"https://sctapi.ftqq.com/{sckey}.send"
            
            data = {
                'title': title,
                'desp': content
            }
            
            response = requests.post(url, data=data)
            result = response.json()
            
            if result.get('code') == 0:
                logger.info("Server酱消息发送成功")
                return True
            else:
                logger.error(f"Server酱消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Server酱消息发送异常: {e}")
            return False
    
    def send_trading_signal(self, symbol: str, signal_data: dict) -> bool:
        """发送交易信号通知"""
        signal = signal_data['signal']
        price = signal_data['price']
        reasons = signal_data['reasons']
        strength = signal_data['strength']
        rsi = signal_data.get('rsi', 0)
        volume_ratio = signal_data.get('volume_ratio', 1)
        
        # 构建标题
        action_emoji = "🟢" if signal == 'BUY' else "🔴"
        action_text = "买入信号" if signal == 'BUY' else "卖出信号"
        title = f"{action_emoji} {symbol} {action_text}"
        
        # 构建消息内容
        content = f"""
📊 **交易对**: {symbol}
💰 **当前价格**: ${price:.6f}
📈 **信号强度**: {strength}/10
📊 **RSI**: {rsi:.2f}
📈 **成交量倍数**: {volume_ratio:.2f}x

🎯 **触发原因**:
"""
        
        for i, reason in enumerate(reasons, 1):
            content += f"{i}. {reason}\n"
        
        content += f"\n⏰ **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 添加操作建议
        if signal == 'BUY':
            content += "\n\n💡 **建议**: 考虑建仓，注意风险控制"
        elif signal == 'SELL':
            content += "\n\n💡 **建议**: 考虑减仓或止盈，注意趋势变化"
        
        # 发送通知
        success = False
        
        # 尝试企业微信
        if self.config.get('corp_id'):
            success = self.send_wechat_work_message(title, content)
        
        # 如果企业微信失败，尝试Server酱
        if not success and self.config.get('server_chan_key'):
            success = self.send_server_chan_message(title, content, 
                                                  self.config['server_chan_key'])
        
        return success
    
    def send_daily_summary(self, summary_data: dict) -> bool:
        """发送每日总结"""
        try:
            title = "📊 每日交易信号总结"
            
            content = f"""
📅 **日期**: {datetime.now().strftime('%Y-%m-%d')}

📈 **今日信号统计**:
• 买入信号: {summary_data.get('buy_signals', 0)} 个
• 卖出信号: {summary_data.get('sell_signals', 0)} 个
• 总检测次数: {summary_data.get('total_checks', 0)} 次

🎯 **活跃交易对**:
"""
            
            for symbol, count in summary_data.get('active_symbols', {}).items():
                content += f"• {symbol}: {count} 次信号\n"
            
            if summary_data.get('top_signals'):
                content += "\n🔥 **最强信号**:\n"
                for signal in summary_data['top_signals']:
                    content += f"• {signal['symbol']}: {signal['action']} (强度: {signal['strength']})\n"
            
            # 发送通知
            if self.config.get('corp_id'):
                return self.send_wechat_work_message(title, content)
            elif self.config.get('server_chan_key'):
                return self.send_server_chan_message(title, content, 
                                                   self.config['server_chan_key'])
            
            return False
            
        except Exception as e:
            logger.error(f"发送每日总结失败: {e}")
            return False

# 使用示例
if __name__ == "__main__":
    # 企业微信配置
    wechat_config = {
        'corp_id': 'your_corp_id',
        'corp_secret': 'your_corp_secret',
        'agent_id': 'your_agent_id',
        'to_user': '@all'
    }
    
    # 或者使用Server酱配置
    # wechat_config = {
    #     'server_chan_key': 'your_server_chan_key'
    # }
    
    notifier = WeChatNotifier(wechat_config)
    
    # 测试发送交易信号
    signal_data = {
        'signal': 'BUY',
        'price': 45230.5,
        'strength': 7,
        'reasons': ['RSI从超卖区反弹', '短期均线上穿长期均线', 'MACD金叉'],
        'rsi': 25.3,
        'volume_ratio': 2.1
    }
    
    notifier.send_trading_signal('BTCUSDT', signal_data)