import requests
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, timedelta
import ta
import logging
from typing import List, Dict, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BinanceTrendDetector:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.symbols = []
        self.holding_list = []  # 持仓列表
        self.watch_list = []    # 观察列表
        
        # 技术指标参数
        self.rsi_period = 14
        self.ma_short = 9
        self.ma_long = 21
        self.volume_ma_period = 20
        
        # 微信通知配置（这里使用邮件作为替代，因为微信需要企业微信API）
        self.notification_config = {
            'email': 'your_email@example.com',
            'password': 'your_password',
            'to_email': 'target_email@example.com',
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587
        }
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> pd.DataFrame:
        """获取K线数据"""
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 转换数据类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df[numeric_columns]
            
        except Exception as e:
            logger.error(f"获取{symbol}数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df.empty:
            return df
        
        try:
            # RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.rsi_period).rsi()
            
            # 移动平均线
            df['ma_short'] = ta.trend.SMAIndicator(df['close'], window=self.ma_short).sma_indicator()
            df['ma_long'] = ta.trend.SMAIndicator(df['close'], window=self.ma_long).sma_indicator()
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()
            
            # 布林带
            bollinger = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bollinger.bollinger_hband()
            df['bb_lower'] = bollinger.bollinger_lband()
            df['bb_middle'] = bollinger.bollinger_mavg()
            
            # 成交量移动平均
            df['volume_ma'] = ta.volume.VolumeSMAIndicator(df['close'], df['volume'], 
                                                         window=self.volume_ma_period).volume_sma()
            
            # 随机指标
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            return df
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return df
    
    def detect_trend_reversal(self, df: pd.DataFrame, symbol: str) -> Dict:
        """检测趋势反转信号"""
        if len(df) < 30:  # 需要足够的数据点
            return {'signal': 'HOLD', 'strength': 0, 'reasons': []}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        
        buy_signals = []
        sell_signals = []
        signal_strength = 0
        
        # 1. RSI信号
        if latest['rsi'] < 30 and prev['rsi'] >= 30:
            buy_signals.append("RSI从超卖区反弹")
            signal_strength += 2
        elif latest['rsi'] > 70 and prev['rsi'] <= 70:
            sell_signals.append("RSI进入超买区")
            signal_strength += 2
        
        # 2. 移动平均线交叉
        if (latest['ma_short'] > latest['ma_long'] and 
            prev['ma_short'] <= prev['ma_long']):
            buy_signals.append("短期均线上穿长期均线(金叉)")
            signal_strength += 3
        elif (latest['ma_short'] < latest['ma_long'] and 
              prev['ma_short'] >= prev['ma_long']):
            sell_signals.append("短期均线下穿长期均线(死叉)")
            signal_strength += 3
        
        # 3. MACD信号
        if (latest['macd'] > latest['macd_signal'] and 
            prev['macd'] <= prev['macd_signal']):
            buy_signals.append("MACD金叉")
            signal_strength += 2
        elif (latest['macd'] < latest['macd_signal'] and 
              prev['macd'] >= prev['macd_signal']):
            sell_signals.append("MACD死叉")
            signal_strength += 2
        
        # 4. 布林带信号
        if (latest['close'] < latest['bb_lower'] and 
            prev['close'] >= prev['bb_lower']):
            buy_signals.append("价格触及布林带下轨")
            signal_strength += 1
        elif (latest['close'] > latest['bb_upper'] and 
              prev['close'] <= prev['bb_upper']):
            sell_signals.append("价格触及布林带上轨")
            signal_strength += 1
        
        # 5. 成交量确认
        volume_spike = latest['volume'] > latest['volume_ma'] * 1.5
        if volume_spike:
            if buy_signals:
                buy_signals.append("成交量放大确认")
                signal_strength += 1
            elif sell_signals:
                sell_signals.append("成交量放大确认")
                signal_strength += 1
        
        # 6. 随机指标
        if (latest['stoch_k'] > latest['stoch_d'] and 
            prev['stoch_k'] <= prev['stoch_d'] and 
            latest['stoch_k'] < 20):
            buy_signals.append("随机指标低位金叉")
            signal_strength += 1
        elif (latest['stoch_k'] < latest['stoch_d'] and 
              prev['stoch_k'] >= prev['stoch_d'] and 
              latest['stoch_k'] > 80):
            sell_signals.append("随机指标高位死叉")
            signal_strength += 1
        
        # 7. 价格动量
        price_change = (latest['close'] - prev2['close']) / prev2['close']
        if abs(price_change) > 0.03:  # 3%以上变动
            if price_change > 0 and buy_signals:
                buy_signals.append(f"价格强势上涨 {price_change:.2%}")
                signal_strength += 1
            elif price_change < 0 and sell_signals:
                sell_signals.append(f"价格快速下跌 {price_change:.2%}")
                signal_strength += 1
        
        # 决定信号
        signal = 'HOLD'
        reasons = []
        
        if len(buy_signals) >= 2 and signal_strength >= 4:
            signal = 'BUY'
            reasons = buy_signals
        elif len(sell_signals) >= 2 and signal_strength >= 4:
            signal = 'SELL'
            reasons = sell_signals
        
        return {
            'signal': signal,
            'strength': signal_strength,
            'reasons': reasons,
            'price': latest['close'],
            'rsi': latest['rsi'],
            'volume_ratio': latest['volume'] / latest['volume_ma']
        }
    
    def should_notify(self, symbol: str, signal: str) -> bool:
        """判断是否应该发送通知"""
        if signal == 'HOLD':
            return False
        
        if signal == 'BUY':
            # 买入信号：币种不在持仓列表但在观察列表
            return symbol not in self.holding_list and symbol in self.watch_list
        
        elif signal == 'SELL':
            # 卖出信号：币种在持仓列表
            return symbol in self.holding_list
        
        return False
    
    def send_notification(self, symbol: str, signal_data: Dict):
        """发送微信通知（这里使用邮件模拟）"""
        try:
            signal = signal_data['signal']
            price = signal_data['price']
            reasons = signal_data['reasons']
            strength = signal_data['strength']
            rsi = signal_data['rsi']
            volume_ratio = signal_data['volume_ratio']
            
            # 构建消息
            action = "🟢 买入信号" if signal == 'BUY' else "🔴 卖出信号"
            
            message = f"""
{action} - {symbol}

💰 当前价格: ${price:.6f}
📊 信号强度: {strength}/10
📈 RSI: {rsi:.2f}
📊 成交量倍数: {volume_ratio:.2f}x

🎯 触发原因:
"""
            for i, reason in enumerate(reasons, 1):
                message += f"{i}. {reason}\n"
            
            message += f"\n⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 发送邮件（作为微信通知的替代）
            self.send_email(f"{symbol} {action}", message)
            
            logger.info(f"已发送{symbol}的{signal}信号通知")
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
    
    def send_email(self, subject: str, body: str):
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.notification_config['email']
            msg['To'] = self.notification_config['to_email']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.notification_config['smtp_server'], 
                                self.notification_config['smtp_port'])
            server.starttls()
            server.login(self.notification_config['email'], 
                        self.notification_config['password'])
            
            text = msg.as_string()
            server.sendmail(self.notification_config['email'], 
                          self.notification_config['to_email'], text)
            server.quit()
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
    
    def load_config(self, config_file: str = 'trading_config.json'):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.holding_list = config.get('holding_list', [])
            self.watch_list = config.get('watch_list', [])
            self.symbols = list(set(self.holding_list + self.watch_list))
            
            logger.info(f"加载配置: 持仓{len(self.holding_list)}个, 观察{len(self.watch_list)}个")
            
        except FileNotFoundError:
            # 创建默认配置文件
            default_config = {
                "holding_list": ["BTCUSDT", "ETHUSDT"],
                "watch_list": ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"],
                "notification_settings": {
                    "min_signal_strength": 4,
                    "check_interval": 300
                }
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            logger.info("已创建默认配置文件")
            self.load_config(config_file)
    
    def run_detection(self):
        """执行检测"""
        logger.info(f"开始检测 {len(self.symbols)} 个交易对")
        
        for symbol in self.symbols:
            try:
                # 获取数据
                df = self.get_klines(symbol)
                if df.empty:
                    continue
                
                # 计算技术指标
                df = self.calculate_technical_indicators(df)
                
                # 检测信号
                signal_data = self.detect_trend_reversal(df, symbol)
                
                logger.info(f"{symbol}: {signal_data['signal']} (强度: {signal_data['strength']})")
                
                # 判断是否需要通知
                if self.should_notify(symbol, signal_data['signal']):
                    self.send_notification(symbol, signal_data)
                
                time.sleep(0.5)  # 避免API限制
                
            except Exception as e:
                logger.error(f"处理{symbol}时出错: {e}")
    
    def start_monitoring(self, interval: int = 300):
        """开始监控"""
        logger.info(f"开始监控，检测间隔: {interval}秒")
        
        while True:
            try:
                self.run_detection()
                logger.info(f"等待 {interval} 秒后进行下一次检测...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控过程出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续

# 使用示例
if __name__ == "__main__":
    # 创建检测器实例
    detector = BinanceTrendDetector()
    
    # 加载配置
    detector.load_config()
    
    # 可以手动设置列表（如果不使用配置文件）
    # detector.holding_list = ["BTCUSDT", "ETHUSDT"]
    # detector.watch_list = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
    # detector.symbols = list(set(detector.holding_list + detector.watch_list))
    
    print("币安趋势反转检测系统")
    print("=" * 50)
    
    choice = input("选择运行模式:\n1. 单次检测\n2. 持续监控\n请输入选择 (1/2): ")
    
    if choice == "1":
        detector.run_detection()
    elif choice == "2":
        interval = input("输入检测间隔(秒，默认300): ")
        interval = int(interval) if interval.isdigit() else 300
        detector.start_monitoring(interval)
    else:
        print("无效选择")