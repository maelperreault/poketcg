import sys
import json
import random
import subprocess
import shutil
from collections import Counter
from functools import partial

open_utf8 = partial(open, encoding='utf8')

# The base bit-noise constants were crafted to have distinctive and interesting
# bits, and have so far produced excellent experimental test results.
NOISE1 = 0xb5297a4d  # 0b0110'1000'1110'0011'0001'1101'1010'0100
NOISE2 = 0x68e31da4  # 0b1011'0101'0010'1001'0111'1010'0100'1101
NOISE3 = 0x1b56c4e9  # 0b0001'1011'0101'0110'1100'0100'1110'1001
PRIME1 = 0x0bd4bcb5  # 0b0000'1011'1101'0100'1011'1100'1011'0101
PRIME2 = 0x0063d68d  # 0b0000'0000'0110'0011'1101'0110'1000'1101

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


class PTCGRando:
    RAND_CARDS = 10
    RAND_NPC_DECKS = 20
    RAND_BOOSTERS = 30
    RAND_MASTERS = 40
    RAND_STARTER_DECKS = 50

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
        self.exclude_prize = False
        # Enabling randomizes prizes from 1-6
        self.prize_full_random = False
        # While prize_full_random is disabled, adds from -prize_range to +prize_range
        self.prize_range = 1

        # Disable randomizing trainer decks
        self.exclude_decks = False

        # Disable randomizing music
        self.exclude_music = False

        # BOOSTER REWARDS
        self.exclude_boosters = False

        # Enabling randomizes booster rewards from booster_min to booster_max
        self.booster_min = 1
        self.booster_max = 6

        # DECK GENERATION
        self.min_pokemon = 20
        self.max_pokemon = 32
        self.min_trainer = 5
        self.max_trainer = 12

    def pkmn_by_evolution(cards, has_evolution=False):
        return filter(lambda x: x['has_evolution'] == has_evolution, cards)

    def pkmn_by_stage(cards, stage=STAGE_BASIC):
        return filter(lambda x: x['stage'] == stage, cards)

    def pkmn_by_energy(cards, energy):
        return filter(lambda x: energy in x['energy'], cards)

    def pkmn_colorless(cards):
        return filter(lambda x: ('COLORLESS' in x['energy'], len(x['energy'])) == (True, 1), cards)

    def load_data(self, data_file, cards_file):
        with open_utf8(data_file) as file:
            self.data = json.load(file)
        with open_utf8(cards_file) as file:
            self.data['cards'] = json.load(file)
            card_list = self.data['cards'].values()
            self.data['pokemon_cards'] = list(filter(lambda x: x['type'] == PTCGRando.TYPE_PKMN, card_list))
            self.data['energy_cards'] = list(filter(lambda x: x['type'] == PTCGRando.TYPE_ENERGY, card_list))
            self.data['trainer_cards'] = list(filter(lambda x: x['type'] == PTCGRando.TYPE_TRAINER, card_list))

    def randomize_cards(self):
        current_card = ''
        with open_utf8('templates/cards.asm', 'r') as src, open_utf8('src/data/cards.asm', 'w') as target:
            for i, line in enumerate(src):
                if 'CARD_NAME' in line:
                    current_card = line.split(':')[0]
                    target.write(line)
                elif 'RANDOMIZE_RARITY' in line:
                    # @Todo add rarity randomizing?
                    target.write(line)
                elif 'RANDOMIZE_SET' in line:
                    y = self.data['cards'][current_card]['group'] if self.group_by_evolution else self.data['cards'][current_card]['id']
                    y *= 10
                    target.write('	db %s | NONE ; sets\n' % pick(self.data['sets'], noise2d(PTCGRando.RAND_CARDS, y, self.seed)))
                else:
                    target.write(line)

    def write_duel(self, target, line):
        trainer = self.data['npc_duels'][line.split(':')[1].strip()]
        y = trainer['id'] * 10
        prize = trainer['prize']
        deck_id = trainer['deck_id']
        music_id = trainer['music_id']
        if not self.exclude_prize:
            if self.prize_full_random:
                prize = calc_range(noise3d(PTCGRando.RAND_NPC_DECKS, y, 10, self.seed), 1, 6)
            else:
                prize = calc_offset(prize, self.prize_range, noise3d(PTCGRando.RAND_NPC_DECKS, y, 10, self.seed))
                if prize < 1:
                    prize = 1
                elif prize > 6:
                    prize = 6
        if not self.exclude_decks:
            deck_id = pick(self.data['decks'], noise3d(PTCGRando.RAND_NPC_DECKS, y, 20, self.seed))
        if not self.exclude_music:
            music_id = pick(self.data['music'], noise3d(PTCGRando.RAND_NPC_DECKS, y, 30, self.seed))
        target.write('	start_duel PRIZES_{}, {}, {}\n'.format(prize, deck_id, music_id))

    def write_boosters(self, target, line):
        trainer = self.data['npc_boosters'][line.split(':')[1].strip()]
        y = trainer['id'] * 10
        z = 10
        booster_count = 0
        boosters = []
        if self.exclude_boosters:
            boosters = trainer['packs']
        else:
            booster_count = calc_range(noise3d(PTCGRando.RAND_BOOSTERS, y, z, self.seed), self.booster_min, self.booster_max)
            if booster_count < 1:
                booster_count = 1
            for i in range(booster_count):
                z += 10
                boosters.append(pick(self.data['packs'], noise3d(PTCGRando.RAND_BOOSTERS, y, z, self.seed)))

        remainder = booster_count % 3
        if remainder > 0:
            boosters += ['NO_BOOSTER'] * (3 - remainder)
        booster_count = len(boosters)

        while len(boosters) >= 3:
            booster_set = boosters[:3]
            boosters = boosters[3:]
            target.write('	give_booster_packs {}\n'.format(', '.join(booster_set)))

    def write_master_check(self, target, line):
        if len(self.data['master_checks']) == 0:
            return
        patch_file = pick(self.data['master_checks'], noise2d(PTCGRando.RAND_MASTERS, self.data['masters_checked'], self.seed))
        self.data['master_checks'].remove(patch_file)
        with open_utf8(patch_file, 'r') as patch:
            target.writelines(patch.readlines())
        self.data['masters_checked'] = self.data['masters_checked'] + 10

    def randomize_bank03(self):
        self.data['master_checks'] = [
            'templates/patches/isaac_check.asm',
            'templates/patches/ken_check.asm',
            'templates/patches/mitch_check.asm',
            'templates/patches/murray_check.asm'
        ]
        self.data['masters_checked'] = 0
        with open_utf8('templates/bank03.asm', 'r') as src, open_utf8('src/engine/bank03.asm', 'w') as target:
            for i, line in enumerate(src):
                if '; DUEL:' in line:
                    self.write_duel(target, line)
                elif '; BOOSTERS:' in line:
                    self.write_boosters(target, line)
                elif '; MASTER_CHECK:' in line:
                    self.write_master_check(target, line)
                    target.write(line)
                else:
                    target.write(line)

    def randomize_bank04(self):
        with open_utf8('templates/bank04.asm', 'r') as src, open_utf8('src/engine/bank04.asm', 'w') as target:
            for i, line in enumerate(src):
                target.write(line)

    def generate_deck(self, target, z):
        y = 10
        remaining_trainer = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
        remaining_trainer = calc_range(remaining_trainer, self.min_trainer, self.max_trainer)
        y += 10
        remaining_pokemon = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed)
        remaining_pokemon = calc_range(remaining_pokemon, self.min_pokemon, self.max_pokemon)
        y += 10
        color_count = noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed) % 10
        if color_count < 3:
            color_count = 1
        elif color_count < 9:
            color_count = 2
        else:
            color_count = 3
        colors = self.data['colors'].copy()
        y += 10
        if noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed) % 2 == 1:
            colors.remove('COLORLESS')
        while len(colors) > color_count:
            color = colors[noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed) % len(colors)]
            colors.remove(color)
            y += 10

        cards = Counter()

        while remaining_trainer > 0:
            card = pick(self.data['trainer_cards'], noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed))
            if cards[card['constant']] < card['limit']:
                cards[card['constant']] += 1
                remaining_trainer -= 1
            y += 10

        pokemons = []
        for color in colors:
            if color == 'COLORLESS':
                pokemons += PTCGRando.pkmn_colorless(self.data['pokemon_cards'])
            else:
                pokemons += PTCGRando.pkmn_by_energy(self.data['pokemon_cards'], color)

        while remaining_pokemon > 0:
            card = pick(pokemons, noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed))
            if cards[card['constant']] < card['limit']:
                cards[card['constant']] += 1
                remaining_pokemon -= 1
                if card['has_evolution'] and card['target_group']:
                    pre_evo = next(filter(lambda x: x['text_name'] == card['target_group'], self.data['cards'].values()))
                    if cards[pre_evo['constant']] < pre_evo['limit']:
                        cards[pre_evo['constant']] += 1
                        remaining_pokemon -= 1
                    if pre_evo['has_evolution'] and pre_evo['target_group']:
                        pre_evo2 = next(filter(lambda x: x['text_name'] == pre_evo['target_group'], self.data['cards'].values()))
                        if cards[pre_evo2['constant']] < pre_evo2['limit']:
                            cards[pre_evo2['constant']] += 1
                            remaining_pokemon -= 1
            y += 10

        energies = []
        for color in colors:
            energies.append(self.data['cards'][self.data['energies'][color]])
        remaining_energies = 60 - sum(cards.values())

        while remaining_energies > 0:
            card = pick(energies, noise3d(PTCGRando.RAND_STARTER_DECKS, y, z, self.seed))
            if cards[card['constant']] < card['limit']:
                cards[card['constant']] += 1
                remaining_energies -= 1
            y += 10

        for k in cards:
            target.write(' db {}, {}\n'.format(cards[k], k))

    def randomize_decks(self):
        with open_utf8('templates/decks.asm', 'r') as src, open_utf8('src/data/decks.asm', 'w') as target:
            z = 10
            for i, line in enumerate(src):
                if '; GENERATE_DECK:' in line:
                    self.generate_deck(target, z)
                    z += 10
                target.write(line)

    def randomize_text_offsets(self):
        with open_utf8('templates/text_offsets.asm', 'r') as src, open_utf8('src/text/text_offsets.asm', 'w') as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text2(self):
        with open_utf8('templates/text2.asm', 'r') as src, open_utf8('src/text/text2.asm', 'w') as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text3(self):
        with open_utf8('templates/text3.asm', 'r') as src, open_utf8('src/text/text3.asm', 'w') as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text4(self):
        with open_utf8('templates/text4.asm', 'r') as src, open_utf8('src/text/text4.asm', 'w') as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text7(self):
        with open_utf8('templates/text7.asm', 'r') as src, open_utf8('src/text/text7.asm', 'w') as target:
            for i, line in enumerate(src):
                target.write(line)

    def randomize_text8(self):
        with open_utf8('templates/text8.asm', 'r') as src, open_utf8('src/text/text8.asm', 'w') as target:
            for i, line in enumerate(src):
                target.write(line)

seed = random.randint(0, 999999)
if len(sys.argv) > 1:
    seed = int(sys.argv[1])

ptcg = PTCGRando()
ptcg.load_data('data.json', 'cards.json')
ptcg.seed = seed
ptcg.randomize_cards()
ptcg.randomize_bank03()
ptcg.randomize_bank04()
ptcg.randomize_decks()
ptcg.randomize_text_offsets()
ptcg.randomize_text2()
ptcg.randomize_text3()
ptcg.randomize_text4()
ptcg.randomize_text7()
ptcg.randomize_text8()

if sys.platform == 'linux':
    make = subprocess.run(['make'], stdout=subprocess.PIPE, universal_newlines=True)
    if make.returncode == 0:
        shutil.move('poketcg.gbc', 'ptcgr_{:06d}.gbc'.format(seed))
    else:
        print(make.stdout)
