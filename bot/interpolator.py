# bot/interpolator.py
import random

class EMA:
    def __init__(self, alpha=0.15):
        self.alpha = alpha
        self.value = None

    def update(self, price: float) -> float:
        if self.value is None:
            self.value = price
        else:
            self.value = self.alpha * price + (1 - self.alpha) * self.value
        return self.value


class SmoothPriceInterpolator:
    def __init__(self, alpha=0.15, max_change=0.003, steps=5):
        self.alpha = alpha
        self.max_change = max_change
        self.steps = steps
        self.state = {}  # coin별 상태

    def _clamp(self, prev, current):
        diff = current - prev
        limit = prev * self.max_change

        if abs(diff) > limit:
            return prev + limit * (1 if diff > 0 else -1)
        return current

    def smooth(self, coin, new_price):
        """
        차트용 가격 보간
        return: list[float]
        """
        # 최초 가격
        if coin not in self.state:
            ema = EMA(self.alpha)
            ema.update(new_price)

            self.state[coin] = {
                "last": new_price,
                "ema": ema
            }
            return [round(new_price, 4)]

        prev = self.state[coin]["last"]
        ema = self.state[coin]["ema"]

        # 1️⃣ 급격한 점프 제한
        clamped = self._clamp(prev, new_price)

        # 2️⃣ 보간 (프레임 분할)
        delta = (clamped - prev) / self.steps
        interpolated = [prev + delta * i for i in range(1, self.steps + 1)]

        # 3️⃣ EMA + 미세 노이즈
        result = []
        for price in interpolated:
            smooth = ema.update(price)

            noise = smooth * random.uniform(-0.00015, 0.00015)
            result.append(round(smooth + noise, 4))

        self.state[coin]["last"] = clamped
        return result
