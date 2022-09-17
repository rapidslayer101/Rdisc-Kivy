import enclib as enc
from random import seed, uniform
from hashlib import sha512
from time import sleep


def game(odds, seed_inp=None):
    base, above_value = odds.split(":")
    base, above_value = int(base), int(above_value)
    game_ = False
    if not seed_inp:
        game_ = True
        seed_inp = enc.rand_b96_str(48)  # <-- sent after game finishes
    seed(seed_inp[:24]+odds)
    rand_float = uniform(1, above_value)
    if rand_float > base:
        outcome = "LOSE"
    else:
        outcome = "WIN"
    if game_:
        game_hash = enc.to_base(96, 16, sha512(f"{seed_inp[24:36]}_{outcome}_{seed_inp[36:]}".encode()).hexdigest())
        return seed_inp, rand_float, outcome, game_hash
    else:
        return rand_float


def run_test(odds):
    outcomes = []
    counter = 0
    while True:
        counter += 1
        seed_input, rand_float, result, game_hash = game(odds)
        outcomes.append(result)
        #if rand_float == game(odds, seed_input):
        #    print("Game is fair!")
        #else:
        #    print("Game is not fair!")
        #    break
        print(outcomes.count("WIN")/len(outcomes), counter)

#run_test("49:100")


def run_game(odds):
    seed_input, rand_float, result, game_hash = game(odds)
    print(rand_float)
    multiply = 30
    min_val = rand_float/multiply
    number = uniform(1, min_val)
    loop_multiplier = 1
    while loop_multiplier < multiply-1:
        number = round(uniform(number, min_val*loop_multiplier), 2)
        print(number)
        sleep(loop_multiplier*0.03)
        loop_multiplier += 1
    print(rand_float)


run_game("33:100")

