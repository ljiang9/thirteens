"""Thirteens 纸牌接龙（纯本地 CLI）。

规则（经典 Thirteens）：
- 52 张标准牌发 10 堆，每堆 1 张明牌；剩余 42 张为牌库（stock）。
- 数值：A=1, 2..10=面值, J=11, Q=12, K=13。
- 和为 13 的两堆牌可一起移除；K 单独成堆可直接移除。
- 移除后从牌库补牌；所有 52 张牌都移除即获胜；无可走步数且牌未清空即失败。
"""
from __future__ import annotations

import argparse
import random
import sys

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]
NUM_PILES = 10
TARGET = 13


def rank_value(rank: str) -> int:
    return RANKS.index(rank) + 1


def card_value(card: str) -> int:
    """card 形如 'A♠'、'10♥'：返回点数 A=1..K=13。"""
    return rank_value(card[:-1])


def new_deck() -> list[str]:
    return [r + s for s in SUITS for r in RANKS]


def shuffle(deck: list[str], seed: int | None = None) -> None:
    rng = random.Random(seed)
    rng.shuffle(deck)


class Game:
    def __init__(self, seed: int | None = None) -> None:
        deck = new_deck()
        shuffle(deck, seed)
        self.stock: list[str] = deck
        self.piles: list[str | None] = [self.stock.pop() for _ in range(NUM_PILES)]
        self.moves = 0
        self.removed = 0

    # ---- 查询 ----
    def stock_left(self) -> int:
        return len(self.stock)

    def is_won(self) -> bool:
        return self.removed == 52

    def is_stuck(self) -> bool:
        return not self.is_won() and not self.find_moves()

    def find_moves(self) -> list[tuple[int, int | None]]:
        """返回所有合法走法：(堆下标, 另一堆下标) 或 (堆下标, None) 表示单张 K。"""
        moves: list[tuple[int, int | None]] = []
        live = [(i, self.piles[i]) for i in range(NUM_PILES) if self.piles[i] is not None]
        for i, card in live:
            if card_value(card) == TARGET:
                moves.append((i, None))
        for a in range(len(live)):
            for b in range(a + 1, len(live)):
                i, card_a = live[a]
                j, card_b = live[b]
                if card_value(card_a) + card_value(card_b) == TARGET:
                    moves.append((i, j))
        return moves

    # ---- 落子 ----
    def _refill(self, idx: int) -> None:
        if self.stock:
            self.piles[idx] = self.stock.pop()
        else:
            self.piles[idx] = None

    def remove(self, idxs: list[int]) -> None:
        """移除一堆或两堆牌并从牌库补牌。调用前应先用 find_moves/校验保证合法。"""
        if len(idxs) == 1:
            card = self.piles[idxs[0]]
            if card is None or card_value(card) != TARGET:
                raise ValueError("只有 K 可以单张移除")
        elif len(idxs) == 2:
            a, b = idxs
            ca, cb = self.piles[a], self.piles[b]
            if ca is None or cb is None or card_value(ca) + card_value(cb) != TARGET:
                raise ValueError("这两堆牌之和不为 13")
        else:
            raise ValueError("一次只能移除 1 或 2 堆牌")
        for i in idxs:
            self._refill(i)
        self.removed += len(idxs)
        self.moves += 1

    def remove_king(self, idx: int) -> None:
        self.remove([idx])

    def remove_pair(self, a: int, b: int) -> None:
        self.remove([a, b])


# ---------------- CLI ----------------

def render(game: Game) -> str:
    lines = [f"牌库剩余: {game.stock_left()}  已移除: {game.removed}/52  步数: {game.moves}"]
    for i, card in enumerate(game.piles):
        mark = "·" if card is None else card
        lines.append(f"  {i + 1:>2}: {mark}")
    return "\n".join(lines)


def auto_play(game: Game, verbose: bool = True) -> str:
    """自动走子：优先移除 K，否则按发现顺序走第一个对子。必然终止（每步减少牌数）。"""
    while not game.is_won():
        moves = game.find_moves()
        if not moves:
            if verbose:
                print(render(game))
                print("无可走步数，失败。")
            return "lose"
        idx, other = moves[0]
        if other is None:
            if verbose:
                print(f"移除 K: {game.piles[idx]}（第 {idx + 1} 堆）")
            game.remove_king(idx)
        else:
            if verbose:
                print(f"移除对子: {game.piles[idx]} + {game.piles[other]}（第 {idx + 1}/{other + 1} 堆）")
            game.remove_pair(idx, other)
        if verbose and game.moves % 10 == 0:
            print(f"  …已移除 {game.removed}/52，牌库 {game.stock_left()}")
    if verbose:
        print(render(game))
        print(f"🎉 获胜！共用 {game.moves} 步。")
    return "win"


def play_interactive(seed: int | None) -> int:
    game = Game(seed)
    print("=== Thirteens 纸牌接龙 ===")
    print("指令：输入两个堆号移除和为 13 的对子（如 3 8）；K 直接输入 k 堆号（如 k 5）；q 退出。")
    while True:
        print()
        print(render(game))
        if game.is_won():
            print(f"🎉 获胜！共用 {game.moves} 步。")
            return 0
        moves = game.find_moves()
        if not moves:
            print("无可走步数，失败。再来一局吧！")
            return 1
        print(f"（合法走法 {len(moves)} 个）")
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            return 0
        if raw in ("q", "quit", "退出"):
            print("退出。")
            return 0
        if raw in ("n", "new", "新局"):
            game = Game(seed)
            print("已开新局。")
            continue
        parts = raw.split()
        try:
            if len(parts) == 2 and parts[0] == "k":
                idx = int(parts[1]) - 1
                game.remove_king(idx)
            elif len(parts) == 2:
                a, b = int(parts[0]) - 1, int(parts[1]) - 1
                if a == b:
                    print("两堆不能相同。")
                    continue
                game.remove_pair(a, b)
            else:
                print("格式不对：如 `3 8` 移除对子，`k 5` 移除 K，`q` 退出。")
                continue
        except (ValueError, IndexError) as e:
            print(f"不合法：{e}")
            continue
    # 不可达
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thirteens 纸牌接龙（纯本地）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--auto", action="store_true", help="自动走子演示")
    args = parser.parse_args(argv)
    if args.auto:
        game = Game(args.seed)
        result = auto_play(game)
        return 0 if result == "win" else 1
    return play_interactive(args.seed)


if __name__ == "__main__":
    sys.exit(main())
