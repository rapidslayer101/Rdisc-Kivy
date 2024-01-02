from enclib import rand_b96_str, to_base
from random import seed, uniform, randint
from hashlib import sha512


def coin_game(odds, seed_inp=None):
    base, above_value = odds.split(":")
    base, above_value = int(base), int(above_value)+int(base)
    game_ = False
    if not seed_inp:
        game_ = True
        seed_inp = rand_b96_str(48)  # <-- sent after game finishes
    seed(seed_inp[:24]+odds)
    rand_float = uniform(1, above_value)
    if rand_float > base:
        outcome = "red"
    else:
        outcome = "green"
    if game_:
        game_hash = to_base(96, 16, sha512(f"{seed_inp[24:randint(25,36)]}_{outcome}_"
                                           f"{seed_inp[randint(25,36):]}".encode()).hexdigest())
        return seed_inp, rand_float, outcome, game_hash
    else:
        return rand_float


def run_test(odds):
    outcomes = []
    counter = 0
    while True:
        counter += 1
        seed_input, rand_float, result, game_hash = coin_game(odds)
        outcomes.append(result)
        if rand_float == coin_game(odds, seed_input):
            print("Game is fair!")
        else:
            print("Game is not fair!")
            break
        print(outcomes.count("WIN")/len(outcomes), counter)
