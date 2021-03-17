import json


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
    RAND_DECKS = 20
    RAND_BOOSTERS = 30

    def __init__(self):
        self.seed = 1
        self.data = None

        # CARDS
        # Groups evolutioary lines in the same boosters
        self.group_by_evolution = False

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
        self.booster_full_random = False
        self.booster_min = 1
        self.booster_max = 6

        # While booster_full_random is disabled, adds from -booster_range to +booster_range
        self.booster_range = 2

    def load_data(self, filename):
        with open(filename) as file:
            self.data = json.load(file)

    def randomize_cards(self):
        current_card = ''
        with open('templates/cards.asm', 'r') as src, open('src/data/cards.asm', 'w') as target:
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

    def randomize_bank03(self):
        with open('templates/bank03.asm', 'r') as src, open('src/engine/bank03.asm', 'w') as target:
            for i, line in enumerate(src):
                if '; DUEL:' in line:
                    trainer = self.data['npc_duels'][line.split(':')[1].strip()]
                    y = trainer['id'] * 10
                    prize = trainer['prize']
                    deck_id = trainer['deck_id']
                    music_id = trainer['music_id']
                    if not self.exclude_prize:
                        if self.prize_full_random:
                            prize = calc_range(noise3d(PTCGRando.RAND_DECKS, y, 10, self.seed), 1, 6)
                        else:
                            prize = calc_offset(prize, self.prize_range, noise3d(PTCGRando.RAND_DECKS, y, 10, self.seed))
                            if prize < 1:
                                prize = 1
                            elif prize > 6:
                                prize = 6
                    if not self.exclude_decks:
                        deck_id = pick(self.data['decks'], noise3d(PTCGRando.RAND_DECKS, y, 20, self.seed))
                    if not self.exclude_music:
                        music_id = pick(self.data['music'], noise3d(PTCGRando.RAND_DECKS, y, 30, self.seed))
                    target.write('	start_duel PRIZES_{}, {}, {}\n'.format(prize, deck_id, music_id))
                elif '; BOOSTERS:' in line:
                    trainer = self.data['npc_boosters'][line.split(':')[1].strip()]
                    y = trainer['id'] * 10
                    z = 10
                    booster_count = 0
                    boosters = []
                    if self.exclude_boosters:
                        boosters = trainer['packs']
                    else:
                        if self.booster_full_random:
                            booster_count = calc_range(noise3d(PTCGRando.RAND_BOOSTERS, y, z, self.seed), self.booster_min, self.booster_max)
                        else:
                            booster_count = len(trainer['packs'])
                            booster_count = calc_offset(booster_count, self.booster_range, noise3d(PTCGRando.RAND_BOOSTERS, y, z, self.seed))
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
                else:
                    target.write(line)

ptcg = PTCGRando()
ptcg.load_data('data.json')
ptcg.seed = 123
ptcg.randomize_cards()
ptcg.randomize_bank03()

for i in range(100):
    calc_offset(0, 10, i)
