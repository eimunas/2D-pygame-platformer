"""The player's progress - saved to a small JSON file:
cleared stages, coins (wallet + which coins were already found) and items bought.

    progress = Progress(settings.SAVE_FILE)
    progress.is_unlocked(2)       # stage 1 is always open; stage N needs stage N-1 cleared
    progress.mark_cleared(0)      # saves right away
    progress.collect_coin("Shrine Hill#0")     # +1 coin; that coin never appears again
    progress.buy("bow", 3)        # spend coins, add the item
    progress.use_item("bomb")     # a thrown bomb is gone

Stages are remembered by name, so reordering LEVELS doesn't mix them up.
A missing or broken save file simply means "nothing cleared yet".
"""

import json
import os

from src.level import LEVELS


class Progress:
    def __init__(self, path):
        self.path = path
        self.cleared = set()
        self.coins = 0                 # in the wallet
        self.coins_found = set()       # coin ids already collected ("Stage name#n")
        self.inventory = {}            # item id -> how many
        self.equipped = "katana"       # weapon id (see settings.WEAPONS)
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.cleared = {name for name in data.get("cleared", []) if isinstance(name, str)}
            self.coins = max(0, int(data.get("coins", 0)))
            self.coins_found = {c for c in data.get("coins_found", []) if isinstance(c, str)}
            self.inventory = {k: int(v) for k, v in data.get("inventory", {}).items() if int(v) > 0}
            self.equipped = str(data.get("equipped", "katana"))
        except (OSError, ValueError, AttributeError, TypeError):
            self.cleared, self.coins, self.coins_found, self.inventory = set(), 0, set(), {}
            self.equipped = "katana"

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"cleared": sorted(self.cleared), "coins": self.coins,
                           "coins_found": sorted(self.coins_found),
                           "inventory": self.inventory, "equipped": self.equipped}, f, indent=2)
        except OSError as e:
            print(f"[progress] couldn't save to {self.path}: {e}")

    def is_cleared(self, index):
        return LEVELS[index]["name"] in self.cleared

    def is_unlocked(self, index):
        return index == 0 or self.is_cleared(index - 1)

    def mark_cleared(self, index):
        name = LEVELS[index]["name"]
        if name not in self.cleared:
            self.cleared.add(name)
            self.save()

    # ------------------------------------------------------------ coins & items
    def has_found(self, coin_id):
        return coin_id in self.coins_found

    def collect_coin(self, coin_id):
        if coin_id not in self.coins_found:
            self.coins_found.add(coin_id)
            self.coins += 1
            self.save()

    def item_count(self, item_id):
        return self.inventory.get(item_id, 0)

    def buy(self, item_id, price):
        """Spend coins on an item. Returns False if there aren't enough coins."""
        if self.coins < price:
            return False
        self.coins -= price
        self.inventory[item_id] = self.item_count(item_id) + 1
        self.save()
        return True

    def use_item(self, item_id):
        """Use up one of an item (e.g. a thrown bomb). Returns how many are left."""
        left = max(0, self.item_count(item_id) - 1)
        if left:
            self.inventory[item_id] = left
        else:
            self.inventory.pop(item_id, None)
        self.save()
        return left

    def equip(self, weapon_id):
        if weapon_id != self.equipped:
            self.equipped = weapon_id
            self.save()

    def reset(self):
        self.cleared.clear()
        self.coins, self.coins_found, self.inventory = 0, set(), {}
        self.equipped = "katana"
        self.save()
