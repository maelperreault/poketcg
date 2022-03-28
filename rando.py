#!/usr/bin/python3

import sys
import json
import random
import subprocess
import shutil
from collections import Counter
from functools import partial
from enum import IntEnum

open_utf8 = partial(open, encoding="utf8")

# The base bit-noise constants were crafted to have distinctive and interesting
# bits, and have so far produced excellent experimental test results.
NOISE1 = 0xB5297A4D  # 0b0110'1000'1110'0011'0001'1101'1010'0100
NOISE2 = 0x68E31DA4  # 0b1011'0101'0010'1001'0111'1010'0100'1101
NOISE3 = 0x1B56C4E9  # 0b0001'1011'0101'0110'1100'0100'1110'1001
PRIME1 = 0x0BD4BCB5  # 0b0000'1011'1101'0100'1011'1100'1011'0101
PRIME2 = 0x0063D68D  # 0b0000'0000'0110'0011'1101'0110'1000'1101

CAP = 1 << 32


def noise1d(n, seed=0):
    n *= NOISE1
    n += seed
    n ^= n >> 8
    n += NOISE2
    n ^= n << 8
    n *= NOISE3
    n ^= n >> 8
    return n % CAP


def noise2d(x, y, seed=0):
    return noise1d(x + PRIME1 * y, seed)


def noise3d(x, y, z, seed=0):
    return noise1d(x + PRIME1 * y + PRIME2 * z, seed)


def pick(l, n):
    return l[n % len(l)]


def calc_offset(p, r, n):
    offset = (n % (r * 2 + 1)) - r
    return p + offset


def calc_range(p, min, max):
    return p % (max - min + 1) + min


def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


class PokemonEvolutionType(IntEnum):
    BASIC_NO_EVOLUTION = 0
    BASIC_ONE_EVOLUTION = 1
    EVO1_ONE_EVOLUTION = 2
    BASIC_TWO_EVOLUTION = 3
    EVO1_TWO_EVOLUTION = 4
    EVO2_TWO_EVOLUTION = 5


class PTCGRando:
    RAND_CARDS = 10
    RAND_NPC_DECKS = 20
    RAND_BOOSTERS = 30
    RAND_MASTERS = 40
    RAND_STARTER_DECKS = 50
    RAND_NPC_NAMES = 60

    TYPE_PKMN = 0
    TYPE_ENERGY = 1
    TYPE_TRAINER = 2

    STAGE_BASIC = 0
    STAGE_1 = 1
    STAGE_2 = 2
    STAGE_NONE = 3

    def __init__(self):
        self.seed = 1
        self.data = None

        # CARDS
        # Groups evolutioary lines in the same boosters
        self.group_by_evolution = True

        # TRAINERS
        # Disable randomizing prize counts
        self.exclude_prize = True
        # Enabling randomizes prizes from 1-6
        self.prize_full_random = False
        # While prize_full_random is disabled, adds from -prize_range to +prize_range
        self.prize_range = 1
        self.prize_min = 1
        self.prize_max = 6

        # Disable randomizing trainer decks
        self.exclude_decks = False

        # Disable randomizing music
        self.exclude_music = False

        # BOOSTER REWARDS
        self.exclude_boosters = False

        # Enabling randomizes booster rewards from booster_min to booster_max
        self.booster_original_amount = True
        self.booster_min = 1
        self.booster_max = 6

        # DECK GENERATION
        self.min_pokemon = 36
        self.max_pokemon = 36
        self.min_trainer = 5
        self.max_trainer = 10
        self.starter_color_min = 3
        self.starter_color_max = 3

        self.exclude_npcs = False

    def pkmn_by_evolution(cards, has_evolution=False):
        return filter(lambda x: x["has_evolution"] == has_evolution, cards)

    def pkmn_by_stage(cards, stage=STAGE_BASIC):
        return filter(lambda x: x["stage"] == stage, cards)

    def pkmn_by_energy(cards, energy):
        return filter(lambda x: x["card_group"] == energy, cards)

    def pkmn_colorless(cards):
        return filter(lambda x: ("COLORLESS" in x["energy"], len(x["energy"])) == (True, 1), cards)

    def load_data(self, data_file, cards_file, npcs_file):
        with open_utf8(data_file) as file:
            self.data = json.load(file)
        with open_utf8(cards_file) as file:
            self.data["cards"] = json.load(file)
            card_list = self.data["cards"].values()
            self.data["pokemon_cards"] = list(filter(lambda x: x["type"] == PTCGRando.TYPE_PKMN, card_list))
            self.data["energy_cards"] = list(filter(lambda x: x["type"] == PTCGRando.TYPE_ENERGY, card_list))
            self.data["trainer_cards"] = list(filter(lambda x: x["type"] == PTCGRando.TYPE_TRAINER, card_list))
        with open_utf8(npcs_file) as file:
            self.data["npcs"] = json.load(file)

    # Randomize each card (hp, attacks, weakness, etc.)
    def randomize_cards(self):
        # {
        current_card = ""
        with open_utf8("templates/cards.asm", "r") as src, open_utf8("src/data/cards.asm", "w") as target:
            lines = src.readlines()

            default_attack = [None, None, None, None, None, None]
            default_attack[
                PokemonEvolutionType.BASIC_NO_EVOLUTION
            ] = """\tenergy COLORLESS, 1 ; energies
                \ttx TackleName ; name
                \tdw NONE ; description
                \tdw NONE ; description (cont)
                \tdb 10 ; damage
                \tdb DAMAGE_NORMAL ; category
                \tdw NONE ; effect commands
                \tdb NONE ; flags 1
                \tdb NONE ; flags 2
                \tdb NONE ; flags 3
                \tdb 0
                \tdb ATK_ANIM_HIT ; animation"""

            default_attack[PokemonEvolutionType.BASIC_ONE_EVOLUTION] = default_attack[
                PokemonEvolutionType.BASIC_NO_EVOLUTION
            ]
            default_attack[PokemonEvolutionType.BASIC_TWO_EVOLUTION] = default_attack[
                PokemonEvolutionType.BASIC_NO_EVOLUTION
            ]

            default_attack[
                PokemonEvolutionType.EVO1_ONE_EVOLUTION
            ] = """\tenergy COLORLESS, 2 ; energies
                \ttx PoundName ; name
                \tdw NONE ; description
                \tdw NONE ; description (cont)
                \tdb 20 ; damage
                \tdb DAMAGE_NORMAL ; category
                \tdw NONE ; effect commands
                \tdb NONE ; flags 1
                \tdb NONE ; flags 2
                \tdb NONE ; flags 3
                \tdb 0
                \tdb ATK_ANIM_HIT ; animation"""

            default_attack[PokemonEvolutionType.EVO1_TWO_EVOLUTION] = default_attack[
                PokemonEvolutionType.BASIC_NO_EVOLUTION
            ]

            default_attack[
                PokemonEvolutionType.EVO2_TWO_EVOLUTION
            ] = """\tenergy COLORLESS, 3 ; energies
                \ttx SlashName ; name
                \tdw NONE ; description
                \tdw NONE ; description (cont)
                \tdb 20 ; damage
                \tdb DAMAGE_NORMAL ; category
                \tdw NONE ; effect commands
                \tdb NONE ; flags 1
                \tdb NONE ; flags 2
                \tdb NONE ; flags 3
                \tdb 0
                \tdb ATK_ANIM_SLASH ; animation"""

            damage_attacks = [list(), list(), list(), list(), list(), list()]
            non_damage_attacks = [list(), list(), list(), list(), list(), list()]

            # Read all attacks
            i = 0
            while i < len(lines):
                line = lines[i]

                if "CARD_NAME" in line:
                    current_card = line.split(":")[0]
                    current_type = lines[i + 1].split(" ")[1][10:]

                    pokemon_evolution_type = PokemonEvolutionType.BASIC_NO_EVOLUTION

                    card = list(
                        filter(
                            lambda x: x["name"] == current_card,
                            self.data["pokemon_cards"],
                        )
                    )
                    if card and "TYPE_PKMN" in lines[i + 1]:
                        evo1 = list(
                            filter(
                                lambda x: x["target_group"] == card[0]["text_name"],
                                self.data["pokemon_cards"],
                            )
                        )

                        evo2 = ""
                        if evo1:
                            evo2 = list(
                                filter(
                                    lambda x: x["target_group"] == evo1[0]["text_name"],
                                    self.data["pokemon_cards"],
                                )
                            )

                        stage_line = lines[i + 8]
                        if "BASIC" in stage_line:
                            if evo1 and evo2:
                                pokemon_evolution_type = PokemonEvolutionType.BASIC_TWO_EVOLUTION
                            elif evo1:
                                pokemon_evolution_type = PokemonEvolutionType.BASIC_ONE_EVOLUTION
                        elif "STAGE1" in stage_line:
                            if evo1:
                                pokemon_evolution_type = PokemonEvolutionType.EVO1_TWO_EVOLUTION
                            else:
                                pokemon_evolution_type = PokemonEvolutionType.EVO1_ONE_EVOLUTION
                        else:
                            pokemon_evolution_type = PokemonEvolutionType.EVO2_TWO_EVOLUTION

                # Add each non empty attack to list according to pokemon evolution to be shuffled around
                if "; attack" in line:
                    attack = ""

                    # Don't save the ; attack # here
                    i += 1
                    line = lines[i]

                    is_valid_attack = True
                    while line != "\n":
                        if "NONE ; name" in line:
                            is_valid_attack = False

                        attack += line
                        i += 1
                        line = lines[i]

                    if is_valid_attack:
                        power = attack.split(";")[4].split(" ")[3]
                        if power == "0":
                            non_damage_attacks[pokemon_evolution_type].append(attack)
                        else:
                            damage_attacks[pokemon_evolution_type].append(attack)

                i += 1

            # Ensure at least one damage and non damage attack per pokemon
            for i in PokemonEvolutionType:
                while len(damage_attacks[i]) < 300:
                    random.shuffle(damage_attacks[i])
                    damage_attacks[i].extend(damage_attacks[i])

                while len(non_damage_attacks[i]) < 300:
                    random.shuffle(non_damage_attacks[i])
                    non_damage_attacks[i].extend(non_damage_attacks[i])

            # Shuffle all attacks
            for i in PokemonEvolutionType:
                random.shuffle(non_damage_attacks[i])
                random.shuffle(damage_attacks[i])

            i = 0
            while i < len(lines):
                line = lines[i]

                # Get card name to
                if "CARD_NAME" in line:
                    current_card = line.split(":")[0]
                    current_type = lines[i + 1].split(" ")[1][10:]

                    pokemon_evolution_type = PokemonEvolutionType.BASIC_NO_EVOLUTION

                    card = list(
                        filter(
                            lambda x: x["name"] == current_card,
                            self.data["pokemon_cards"],
                        )
                    )
                    if card and "TYPE_PKMN" in lines[i + 1]:
                        evo1 = list(
                            filter(
                                lambda x: x["target_group"] == card[0]["text_name"],
                                self.data["pokemon_cards"],
                            )
                        )

                        evo2 = ""
                        if evo1:
                            evo2 = list(
                                filter(
                                    lambda x: x["target_group"] == evo1[0]["text_name"],
                                    self.data["pokemon_cards"],
                                )
                            )

                        stage_line = lines[i + 8]
                        if "BASIC" in stage_line:
                            if evo1 and evo2:
                                pokemon_evolution_type = PokemonEvolutionType.BASIC_TWO_EVOLUTION
                            elif evo1:
                                pokemon_evolution_type = PokemonEvolutionType.BASIC_ONE_EVOLUTION
                        elif "STAGE1" in stage_line:
                            if evo1:
                                pokemon_evolution_type = PokemonEvolutionType.EVO1_TWO_EVOLUTION
                            else:
                                pokemon_evolution_type = PokemonEvolutionType.EVO1_ONE_EVOLUTION
                        else:
                            pokemon_evolution_type = PokemonEvolutionType.EVO2_TWO_EVOLUTION

                    target.write(line)

                elif "RANDOMIZE_RARITY" in line:
                    # @Todo add rarity randomizing?
                    target.write(line)

                elif "RANDOMIZE_SET" in line:
                    y = (
                        self.data["cards"][current_card]["group"]
                        if self.group_by_evolution
                        else self.data["cards"][current_card]["id"]
                    )
                    y *= 10
                    noise = noise2d(PTCGRando.RAND_CARDS, y, self.seed)
                    target.write("	db %s | NONE ; sets\n" % pick(self.data["sets"], noise))

                # Randomize hp according to evolution
                elif "; hp" in line:
                    y += 10
                    noise = noise2d(PTCGRando.RAND_CARDS, y, self.seed)

                    hp_mins = [50, 40, 60, 40, 60, 70]
                    hp_maxs = [70, 50, 80, 50, 70, 100]

                    hp_min = hp_mins[pokemon_evolution_type]
                    hp_max = hp_maxs[pokemon_evolution_type]
                    hp = calc_range(noise, hp_min, hp_max)
                    hp = round(hp, -1)

                    target.write("	db %s ; hp\n" % hp)

                # Remove weakness
                elif "; weakness" in line:
                    target.write("	db NONE ; weakness\n")

                # Remove resistances
                elif "; resistance" in line:
                    target.write("	db NONE ; resistance\n")

                # Randomize retreat cost according to evolution
                elif "; retreat cost" in line:
                    y += 10
                    noise = noise2d(PTCGRando.RAND_CARDS, y, self.seed)

                    retreat_cost_mins = [1, 0, 1, 0, 1, 2]
                    retreat_cost_maxs = [3, 1, 3, 1, 2, 3]

                    retreat_cost_min = retreat_cost_mins[pokemon_evolution_type]
                    retreat_cost_max = retreat_cost_maxs[pokemon_evolution_type]
                    retreat_cost = calc_range(noise, retreat_cost_min, retreat_cost_max)

                    target.write("	db %s ; retreat cost\n" % retreat_cost)

                # Randomize attacks by shuffling between pokemon of same evolution stage
                elif "; attack" in line:
                    attack1 = ""
                    attack2 = ""

                    while not attack2:
                        attack = ""

                        attack_name = lines[i + 2]
                        if "NONE ; name" in attack_name:
                            # Empty attack write lines as is
                            while line != "\n":
                                i += 1
                                line = lines[i]
                                attack += line

                            if attack1:
                                attack2 = attack

                                # Force a weak base attack per evolution type if Pokemon has no attack with power
                                power1 = attack1.split(";")[4].split(" ")[3]
                                if power1 == "0":
                                    attack2 = default_attack[pokemon_evolution_type]

                                    cost1 = 0
                                    for digit in attack1.split(";")[0].split(" "):
                                        if digit.isdigit():
                                            cost1 += int(digit)

                                    cost2 = 0
                                    for digit in attack2.split(";")[0].split(" "):
                                        if digit.isdigit():
                                            cost2 += int(digit)

                                    power1 = attack1.split(";")[4].split(" ")[3]
                                    power2 = attack2.split(";")[4].split(" ")[3]

                                    if cost1 > cost2 or (cost1 == cost2 and power1 > power2):
                                        attack1, attack2 = attack2, attack1
                            else:
                                attack1 = attack
                                i += 1
                                line = lines[i]
                        else:
                            # Get an unique random attack
                            if attack1:
                                power1 = attack1.split(";")[4].split(" ")[3]
                                if power1 == "0":
                                    attack = damage_attacks[pokemon_evolution_type].pop()
                                else:
                                    attack = non_damage_attacks[pokemon_evolution_type].pop()
                            else:
                                if random.random() < 0.7:
                                    attack = damage_attacks[pokemon_evolution_type].pop()
                                else:
                                    attack = non_damage_attacks[pokemon_evolution_type].pop()

                            # Replace energy same as pokemon type, colorless keep energy of original attack
                            for energy in [
                                "GRASS,",
                                "FIRE,",
                                "WATER,",
                                "LIGHTNING,",
                                "FIGHTING,",
                                "PSYCHIC,",
                            ]:
                                if energy in attack:
                                    attack = attack.replace(energy, current_type + ",")
                                    break

                            # Skip actual attack lines
                            while line != "\n":
                                i += 1
                                line = lines[i]

                            if attack1:
                                attack2 = attack

                                cost1 = 0
                                for digit in attack1.split(";")[0].split(" "):
                                    if digit[:1].isdigit():
                                        cost1 += int(digit[:1])

                                cost2 = 0
                                for digit in attack2.split(";")[0].split(" "):
                                    if digit[:1].isdigit():
                                        cost2 += int(digit[:1])

                                power1 = attack1.split(";")[4].split(" ")[3]
                                power2 = attack2.split(";")[4].split(" ")[3]

                                if cost1 > cost2 or (cost1 == cost2 and power1 > power2):
                                    attack1, attack2 = attack2, attack1
                            else:
                                attack1 = attack
                                i += 1
                                line = lines[i]

                    # Write ; attack #
                    target.write("\t; attack 1\n")
                    target.write(attack1)
                    target.write("\n")
                    target.write("\t; attack 2\n")
                    target.write(attack2)
                    target.write("\n")

                # Keep all other lines
                else:
                    target.write(line)

                i += 1

    # Generate trainer duels (booster prizes, trainer decks used and music)
    def write_duel(self, target, line):
        # {
        trainer = self.data["npc_duels"][line.split(":")[1].strip()]

        y = trainer["id"] * 10

        prize = trainer["prize"]
        deck_id = trainer["deck_id"]
        music_id = trainer["music_id"]

        if not self.exclude_prize:
            noise = noise3d(PTCGRando.RAND_NPC_DECKS, y, 10, self.seed)

            if self.prize_full_random:
                prize = calc_range(noise, self.prize_min, self.prize_max)
            else:
                prize = calc_offset(prize, self.prize_range, noise)
                prize = clamp(prize, self.prize_min, self.prize_max)

        if not self.exclude_decks:
            noise = noise3d(PTCGRando.RAND_NPC_DECKS, y, 20, self.seed)
            deck_id = pick(self.data["decks"], noise)

        if not self.exclude_music:
            noise = noise3d(PTCGRando.RAND_NPC_DECKS, y, 30, self.seed)
            music_id = pick(self.data["music"], noise)

        target.write("	start_duel PRIZES_{}, {}, {}\n".format(prize, deck_id, music_id))

    # Generate which random booster prizes are awarded by trainers
    def write_boosters(self, target, line):
        trainer = self.data["npc_boosters"][line.split(":")[1].strip()]

        y = trainer["id"] * 10
        z = 10

        booster_count = 0
        boosters = []

        if self.exclude_boosters:
            boosters = trainer["packs"]
        else:
            noise = noise3d(PTCGRando.RAND_BOOSTERS, y, z, self.seed)

            if self.booster_original_amount:
                booster_count = len(trainer["packs"])
            else:
                booster_count = calc_range(noise, self.booster_min, self.booster_max)

            # Generate boosters
            for i in range(booster_count):
                z += 10
                noise = noise3d(PTCGRando.RAND_BOOSTERS, y, z, self.seed)
                booster = pick(self.data["packs"], noise)
                boosters.append(booster)

            # Generate a new event for each group of 3 boosters, as required by game
            remainder = booster_count % 3
            if remainder > 0:
                boosters += ["NO_BOOSTER"] * (3 - remainder)
                booster_count = len(boosters)

            while len(boosters) >= 3:
                booster_set = boosters[:3]
                boosters = boosters[3:]
                target.write("	give_booster_packs {}\n".format(", ".join(booster_set)))

    def write_master_check(self, target, line):
        if len(self.data["master_checks"]) == 0:
            return

        noise = noise2d(PTCGRando.RAND_MASTERS, self.data["masters_checked"], self.seed)
        patch_file = pick(self.data["master_checks"], noise)
        self.data["master_checks"].remove(patch_file)

        with open_utf8(patch_file, "r") as patch:
            target.writelines(patch.readlines())

        self.data["masters_checked"] = self.data["masters_checked"] + 10

    def randomize_bank03(self):
        self.data["master_checks"] = [
            "templates/patches/isaac_check.asm",
            "templates/patches/ken_check.asm",
            "templates/patches/mitch_check.asm",
            "templates/patches/murray_check.asm",
        ]
        self.data["masters_checked"] = 0
        with open_utf8("templates/bank03.asm", "r") as src, open_utf8("src/engine/bank03.asm", "w") as target:
            for i, line in enumerate(src):
                if "; DUEL:" in line:
                    self.write_duel(target, line)
                elif "; BOOSTERS:" in line:
                    self.write_boosters(target, line)
                elif "; MASTER_CHECK:" in line:
                    self.write_master_check(target, line)
                    target.write(line)
                else:
                    target.write(line)

    def randomize_bank04(self):
        with open_utf8("templates/bank04.asm", "r") as src, open_utf8("src/engine/bank04.asm", "w") as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_home(self):
        with open_utf8("templates/home.asm", "r") as src, open_utf8("src/engine/home.asm", "w") as target:
            for i, line in enumerate(src):
                target.write(line)

    # Generates a single base player deck
    def generate_starter_deck(self, target, z, deck_name):
        cards = Counter()

        # Generate deck trainer cards
        y = 10
        noise = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
        remaining_trainer_cards = calc_range(noise, self.min_trainer, self.max_trainer)

        while remaining_trainer_cards > 0:
            y += 10
            noise = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
            card = pick(self.data["trainer_cards"], noise)
            if cards[card["constant"]] < card["limit"]:
                cards[card["constant"]] += 1
                remaining_trainer_cards -= 1

        # Force start with 2 Mysterious Fossil, so Fossil pokemon are sort of playable
        cards["MYSTERIOUS_FOSSIL"] = 2

        # Generate deck pokemon cards
        y += 10
        noise = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
        color_count = calc_range(noise, self.starter_color_min, self.starter_color_min)

        # Generate deck colors
        self.remaining_deck_colors = self.data["colors"].copy()
        random.shuffle(self.remaining_deck_colors)
        colors = self.remaining_deck_colors[:color_count]

        # Name deck according to up to 3 first deck colors
        self.data["starter_deck_names"][deck_name] = ", ".join([color[:6] for color in colors[:3]])

        # Generate a number of cards per color more or less according to min and max
        pokemons = []
        for color in colors:
            y += 10
            noise = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
            min = self.min_pokemon / len(colors)
            max = self.max_pokemon / len(colors)
            remaining_pokemon_cards = calc_range(noise, min, max)

            pokemons = list(PTCGRando.pkmn_by_energy(self.data["pokemon_cards"], color))
            while remaining_pokemon_cards > 0:
                y += 10
                noise = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
                card = pick(pokemons, noise)

                if cards[card["constant"]] < card["limit"]:
                    cards[card["constant"]] += 1
                    remaining_pokemon_cards -= 1

                    if card["has_evolution"] and card["target_group"]:
                        pre_evo = next(
                            filter(
                                lambda x: x["text_name"] == card["target_group"],
                                self.data["cards"].values(),
                            )
                        )

                        if cards[pre_evo["constant"]] < pre_evo["limit"]:
                            cards[pre_evo["constant"]] += 1
                            remaining_pokemon_cards -= 1

                        if pre_evo["has_evolution"] and pre_evo["target_group"]:
                            pre_evo2 = next(
                                filter(
                                    lambda x: x["text_name"] == pre_evo["target_group"],
                                    self.data["cards"].values(),
                                )
                            )

                            if cards[pre_evo2["constant"]] < pre_evo2["limit"]:
                                cards[pre_evo2["constant"]] += 1
                                remaining_pokemon_cards -= 1

        # Add enegies to fill deck
        energies = []
        for color in colors:
            energies.append(self.data["cards"][self.data["energies"][color]])
        remaining_energies = 60 - sum(cards.values())

        while remaining_energies > 0:
            y += 10
            noise = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
            card = pick(energies, noise)
            if cards[card["constant"]] < card["limit"]:
                cards[card["constant"]] += 1
                remaining_energies -= 1

        for k in cards:
            target.write("	db {}, {}\n".format(cards[k], k))

    def randomize_decks(self):
        with open_utf8("templates/decks.asm", "r") as src, open_utf8("src/data/decks.asm", "w") as target:
            z = 10
            for i, line in enumerate(src):
                if "; GENERATE_DECK:" in line:
                    self.generate_starter_deck(target, z, line.split(":")[1].strip())
                    z += 10
                target.write(line)

    def randomize_text_offsets(self):
        with open_utf8("templates/text_offsets.asm", "r") as src, open_utf8("src/text/text_offsets.asm", "w") as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text2(self):
        with open_utf8("templates/text2.asm", "r") as src, open_utf8("src/text/text2.asm", "w") as target:
            for i, line in enumerate(src):
                if "; STARTER_DECK" in line:
                    line = line.format(**self.data["starter_deck_names"])
                target.write(line)

    def randomize_text3(self):
        with open_utf8("templates/text3.asm", "r") as src, open_utf8("src/text/text3.asm", "w") as target:
            y = 10
            npcs = self.data["npcs"].copy()
            self.data["npc_names"] = {}
            for i, line in enumerate(src):
                if "; NPC_NAMES:" in line:
                    if self.exclude_npcs:
                        target.write(line.split(":")[1])
                    else:
                        npc = pick(npcs, noise2d(PTCGRando.RAND_NPC_NAMES, y, self.seed))
                        if "Michael" in line:
                            self.data["npc_names"]["Michael"] = npc
                        elif "Chris" in line:
                            self.data["npc_names"]["Chris"] = npc
                        elif "Jessica" in line:
                            self.data["npc_names"]["Jessica"] = npc
                        elif "Jennifer" in line:
                            self.data["npc_names"]["Jennifer"] = npc
                        elif "Nicholas" in line:
                            self.data["npc_names"]["Nicholas"] = npc
                        elif "Brandon" in line:
                            self.data["npc_names"]["Brandon"] = npc
                        npcs.remove(npc)
                        target.write('	text "{}"\n'.format(npc))
                        y += 10
                elif "; STARTER_DECK" in line:
                    target.write(line.format(**self.data["starter_deck_names"]))
                else:
                    target.write(line)

    def randomize_text4(self):
        with open_utf8("templates/text4.asm", "r") as src, open_utf8("src/text/text4.asm", "w") as target:
            for i, line in enumerate(src):
                if "; MITCH_CHECK:" in line:
                    npc = ""
                    if self.exclude_npcs:
                        if "Michael" in line:
                            npc = "Michael"
                        elif "Chris" in line:
                            npc = "Chris"
                        elif "Jessica" in line:
                            npc = "Jessica"
                    else:
                        if "Michael" in line:
                            npc = self.data["npc_names"]["Michael"]
                        elif "Chris" in line:
                            npc = self.data["npc_names"]["Chris"]
                        elif "Jessica" in line:
                            npc = self.data["npc_names"]["Jessica"]
                    target.write(line.format(npc))
                else:
                    target.write(line)

    def randomize_text5(self):
        with open_utf8("templates/text5.asm", "r") as src, open_utf8("src/text/text5.asm", "w") as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text6(self):
        with open_utf8("templates/text6.asm", "r") as src, open_utf8("src/text/text6.asm", "w") as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text7(self):
        with open_utf8("templates/text7.asm", "r") as src, open_utf8("src/text/text7.asm", "w") as target:
            for i, line in enumerate(src):
                if "; ISAAC_CHECK:" in line:
                    npc = ""
                    if self.exclude_npcs:
                        if "Jennifer" in line:
                            npc = "Jennifer"
                        elif "Nicholas" in line:
                            npc = "Nicholas"
                        elif "Brandon" in line:
                            npc = "Brandon"
                    else:
                        if "Jennifer" in line:
                            npc = self.data["npc_names"]["Jennifer"]
                        elif "Nicholas" in line:
                            npc = self.data["npc_names"]["Nicholas"]
                        elif "Brandon" in line:
                            npc = self.data["npc_names"]["Brandon"]
                    target.write(line.format(npc))
                else:
                    target.write(line)

    def randomize_text8(self):
        with open_utf8("templates/text8.asm", "r") as src, open_utf8("src/text/text8.asm", "w") as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text9(self):
        with open_utf8("templates/text9.asm", "r") as src, open_utf8("src/text/text9.asm", "w") as target:
            for i, line in enumerate(src):
                target.write(line)


seed = random.randint(0, 999999)
if len(sys.argv) > 1:
    seed = int(sys.argv[1])

ptcg = PTCGRando()
ptcg.load_data("data/data.json", "data/cards.json", "data/npc_names.json")
ptcg.seed = seed
ptcg.randomize_cards()
ptcg.randomize_bank03()
ptcg.randomize_bank04()
ptcg.randomize_home()
ptcg.randomize_decks()
ptcg.randomize_text_offsets()
ptcg.randomize_text2()
ptcg.randomize_text3()
ptcg.randomize_text4()
ptcg.randomize_text5()
ptcg.randomize_text6()
ptcg.randomize_text7()
ptcg.randomize_text8()
ptcg.randomize_text9()


def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""

    # from whichcraft import which
    from shutil import which

    return which(name) is not None


# Generates the .ips file using lipx and applies it to create the patched poketcg.gbc ROM
if is_tool("make"):
    make = subprocess.run(["make"], stdout=subprocess.PIPE, universal_newlines=True)
    if make.returncode == 0:
        lipx = subprocess.run(
            [
                "python",
                "lipx.py",
                "-c",
                "baserom.gbc",
                "poketcg.gbc",
                "ptcgr_{:06d}.ips".format(seed),
            ],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        print("Successfully compiled with seed: {:06d}".format(seed))

        # Make a copy of the patched ROM including the time and seed name
        shutil.copyfile("poketcg.gbc", "poketcg_{:06d}.gbc".format(seed))

        sys.exit(0)
    else:
        print(make.stdout)
        sys.exit(1)
