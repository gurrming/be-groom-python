# bot/interpolator.py
import random

class SmoothPriceInterpolator:
    def __init__(self, alpha=0.15):
        self.alpha = alpha
        self.last_price = {}

    def smooth(self, coin, new_price):
        """
        EMA 기반 차트용 보간
        """
        if coin not in self.last_price:
            self.last_price[coin] = new_price
            return round(new_price, 4)

        prev = self.last_price[coin]
        ema = prev + self.alpha * (new_price - prev)

        # 미세 노이즈 (시각적 자연스러움)
        noise = ema * random.uniform(-0.0002, 0.0002)

        final_price = ema + noise
        self.last_price[coin] = final_price

        return round(final_price, 4)
