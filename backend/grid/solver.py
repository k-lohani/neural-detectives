import itertools
from typing import Dict, List, Optional, Tuple

class GridSolver:
    def __init__(self, suspects: List[str], weapons: List[str], locations: List[str]):
        self.suspects = suspects
        self.weapons = weapons
        self.locations = locations
        self.categories = {
            'suspect': suspects,
            'weapon': weapons,
            'location': locations
        }
        
        self.item_to_cat = {}
        for cat, items in self.categories.items():
            for item in items:
                self.item_to_cat[item] = cat
                
        # Grid stores True, False, or None (unknown)
        self.grid: Dict[Tuple[str, str], Optional[bool]] = {}
        # Ensure we only track pairs of different categories
        for cat1, cat2 in itertools.combinations(self.categories.keys(), 2):
            for i1 in self.categories[cat1]:
                for i2 in self.categories[cat2]:
                    self.grid[(i1, i2)] = None
                    self.grid[(i2, i1)] = None

    def get_relation(self, item1: str, item2: str) -> Optional[bool]:
        # Items in same category are mutually exclusive by definition
        if self.item_to_cat[item1] == self.item_to_cat[item2]:
            return True if item1 == item2 else False
        return self.grid.get((item1, item2))

    def set_relation(self, item1: str, item2: str, value: bool) -> bool:
        """
        Sets a direct relation (True or False) and propagates the implications.
        Returns False if a contradiction is detected, True otherwise.
        """
        if self.item_to_cat[item1] == self.item_to_cat[item2]:
            # Can't set cross relation for same category items unless valid
            if item1 == item2 and value is False: return False
            if item1 != item2 and value is True: return False
            return True

        current = self.grid.get((item1, item2))
        if current is not None:
            return current == value
            
        self.grid[(item1, item2)] = value
        self.grid[(item2, item1)] = value

        return self._propagate()

    def _propagate(self) -> bool:
        """
        Loops until no more deductions can be made.
        Returns False if a contradiction is found.
        """
        changed = True
        while changed:
            changed = False
            
            # Rule 1: 1-to-1 Mapping within categories
            # If A is True for B, then A is False for all other items in B's category
            # If A is False for all but ONE item in B's category, that one must be True
            for item in self.item_to_cat.keys():
                cat = self.item_to_cat[item]
                other_cats = [c for c in self.categories.keys() if c != cat]
                for o_cat in other_cats:
                    o_items = self.categories[o_cat]
                    true_rels = [i for i in o_items if self.grid.get((item, i)) is True]
                    false_rels = [i for i in o_items if self.grid.get((item, i)) is False]
                    
                    if len(true_rels) > 1: return False # Contradiction

                    if len(true_rels) == 1:
                        # Set all others to False
                        for i in o_items:
                            if i != true_rels[0] and self.grid.get((item, i)) is not False:
                                self.grid[(item, i)] = False
                                self.grid[(i, item)] = False
                                changed = True
                    
                    if len(false_rels) == len(o_items) - 1:
                        # Only one left, must be True
                        for i in o_items:
                            if self.grid.get((item, i)) is None:
                                self.grid[(item, i)] = True
                                self.grid[(i, item)] = True
                                changed = True
                                
            # Rule 2: Transitivity
            # If A=B and B=C, then A=C
            # If A=B and B!=C, then A!=C
            all_items = list(self.item_to_cat.keys())
            for i, item_a in enumerate(all_items):
                for j, item_b in enumerate(all_items):
                    if i == j: continue
                    rel_ab = self.get_relation(item_a, item_b)
                    if rel_ab is None: continue
                    
                    for k, item_c in enumerate(all_items):
                        if i == k or j == k: continue
                        if self.item_to_cat[item_a] == self.item_to_cat[item_c]: continue # skip same cat target
                        
                        rel_bc = self.get_relation(item_b, item_c)
                        if rel_bc is None: continue
                        
                        rel_ac = self.get_relation(item_a, item_c)
                        
                        if rel_ab is True and rel_bc is True:
                            implied = True
                        elif (rel_ab is True and rel_bc is False) or (rel_ab is False and rel_bc is True):
                            implied = False
                        else:
                            implied = None
                            
                        if implied is not None:
                            if rel_ac is not None:
                                if rel_ac != implied:
                                    return False # Contradiction
                            else:
                                self.grid[(item_a, item_c)] = implied
                                self.grid[(item_c, item_a)] = implied
                                changed = True

        return True

    def check_uniquely_solvable(self) -> bool:
        """
        Verifies if all relationships are determined.
        """
        for val in self.grid.values():
            if val is None:
                return False
        return True
