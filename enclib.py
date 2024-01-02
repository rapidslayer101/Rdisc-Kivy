from datetime import datetime as _datetime_, timedelta as _timedelta_
from sys import byteorder as _byteorder_
from time import perf_counter as _perf_counter_
from os.path import exists as _exists_, getsize as _getsize_
from random import choices as _choices_
from hashlib import sha512 as _sha512_
from zlib import compress as _compress_, decompress as _decompress_
from multiprocessing import Pool as _Pool_, cpu_count as _cpu_count_

# enc 11.10.0 - CREATED BY RAPIDSLAYER101 (Scott Bree)
_default_block_size_ = 5000000  # the chunking size
_xor_salt_len_ = 7  # 94^8 combinations
_default_pass_depth_ = 100000  # the hash loop depth
_b94set_ = "£0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/`!\"$%^&*() -=[{]};:'@#~\\|,<.>"
_b96set_ = _b94set_+"¬?"


# generate a random base 96 string of a given length
def rand_b96_str(num, alpha_set=_b96set_):
    return "".join(_choices_(alpha_set, k=int(num)))


# convert a string to another base
def to_base(base_fr, base_to, hex_to_convert, alpha_set=_b96set_):
    alpha_set, null_fix = alpha_set[:-1], alpha_set[-1]
    if not all([digit in alpha_set[:base_fr] for digit in str(hex_to_convert)]):
        return f"Input contains characters not in the base: {alpha_set[:base_fr]} "
    if 2 > base_to or base_to > len(alpha_set):
        return f"Base out of range 2-{len(alpha_set)}"
    else:
        decimal, power = 0, len(str(hex_to_convert))-1
        for digit in str(hex_to_convert):
            decimal += alpha_set.index(digit)*base_fr**power
            power -= 1
        hexadecimal = ""
        while decimal > 0:
            hexadecimal, decimal = alpha_set[decimal % base_to]+hexadecimal, decimal//base_to
        return hexadecimal


# attempts to find the base of an input string
def get_base(data_to_resolve):
    for i in range(95):
        if to_base(i+2, i+2, data_to_resolve) == data_to_resolve:
            return i+2


# turns a password and salt into a key
# used to save a key so encryption/decryption does not require the generation of a key each time
# can also be used as a string hider to hide data other than a password
def pass_to_key(password, salt, depth=1000000):
    password, salt = password.encode(), salt.encode()
    for i in range(depth):
        password = _sha512_(password+salt).digest()
    return to_base(17, 95, password.hex())


# generates a key of equal length to the data then xor the data with the key
def _xor_(data, key, xor_salt):
    key_value, key = [], key.encode()
    for i in range((len(data)//64)+1):
        key = _sha512_(key+xor_salt).digest()
        key_value.append(key)
    key = b"".join(key_value)[:len(data)]
    return (int.from_bytes(data, _byteorder_) ^ int.from_bytes(key, _byteorder_)).to_bytes(len(data), _byteorder_)


def _encrypter_(enc, text, key, block_size, compressor, file_output=None):
    if enc:
        if type(text) != bytes:
            text = text.encode()
        if compressor:
            text = _compress_(text, 9)
        xor_salt = "".join(_choices_(_b94set_, k=_xor_salt_len_)).encode()
    else:
        xor_salt, text = text[:_xor_salt_len_], text[_xor_salt_len_:]
    if len(text)//block_size < 11 and not file_output:
        if enc:
            return xor_salt+_xor_(text, key, xor_salt)
        elif compressor:
            block = _decompress_(_xor_(text, key, xor_salt))
        else:
            block = _xor_(text, key, xor_salt)
        try:
            return block.decode()
        except UnicodeDecodeError:
            return block
    else:
        text = [text[i:i+block_size] for i in range(0, len(text), block_size)]
        print(f"Generating {len(text)} block keys")
        key1, alpha_gen, counter, keys_salt = int(to_base(95, 17, key), 36), _b94set_, 0, ""
        while len(alpha_gen) > 0:
            counter += 2
            value = int(str(key1)[counter:counter+2]) << 1
            while value > len(alpha_gen)-1:
                value = value // 2
            if len(str(key1)[counter:]) < 2:
                keys_salt += alpha_gen
                alpha_gen = alpha_gen.replace(alpha_gen, "")
            else:
                chosen = alpha_gen[value]
                keys_salt += chosen
                alpha_gen = alpha_gen.replace(chosen, "")
        block_keys = []
        for i in range(len(text)):
            key = pass_to_key(key, keys_salt, 1)
            block_keys.append(key)
        print(f"Launching {len(text)} threads")
        pool = _Pool_(_cpu_count_())
        result_objects = [pool.apply_async(_xor_, args=(text[x], block_keys[x], xor_salt)) for x in range(0, len(text))]
        pool.close()
        if file_output:
            if enc:
                with open(file_output, "wb") as f:
                    for loop, result in enumerate(result_objects):
                        if loop == 0:
                            data = xor_salt+result.get()
                            f.write(data)
                        else:
                            f.write(result.get())
            else:
                d_data = [x.get() for x in result_objects]
                if type(d_data[0]) == bytes:
                    with open(f"{file_output}", "wb") as f:
                        for block in d_data:
                            f.write(block)
                if type(d_data[0]) == str:
                    with open(f"{file_output}", "w", encoding="utf-8") as f:
                        for block in d_data:
                            f.write(block.replace("\r", ""))
                if compressor:
                    with open(f"{file_output}", "rb") as f:
                        data = _decompress_(f.read())
                    with open(f"{file_output}", "wb") as f:
                        f.write(data)
            pool.join()
        else:
            d_data = b""
            for result in result_objects:
                d_data += result.get()
            if enc:
                d_data = xor_salt + d_data
            elif compressor:
                d_data = _decompress_(d_data)
            try:
                d_data = d_data.decode()
            except UnicodeDecodeError:
                pass
            pool.join()
            return d_data


# returns the file size of a file in standard units
def get_file_size(file):
    size, power, n = [_getsize_(file), 2 ** 10, 0]
    power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)}{power_labels[n]}"


# a wrapper for the encrypter function to support file encryption and decryption
def _file_encrypter_(enc, file, key, file_output, compressor):
    start = _perf_counter_()
    if _exists_(file):
        file_name = file.split("/")[-1].split(".")[:-1]  # file_type = file.split("/")[-1].split(".")[-1:]
        print(f"{file_name} is {get_file_size(file)}, should take {round(_getsize_(file)/136731168.599, 2)}s")
        with open(file, 'rb') as hash_file:
            data = hash_file.read()
        _encrypter_(enc, data, key, _default_block_size_, compressor, file_output)
        print(f"ENC/DEC COMPLETE OF {get_file_size(file)} IN {round(_perf_counter_()-start, 2)}s")
    else:
        return "File not found"


# a selection of wrappers for the encrypter function for encryption and decryption

# encrypts data
def enc_from_pass(text, password, salt, depth=_default_pass_depth_, block_size=_default_block_size_):
    return _encrypter_(True, text, pass_to_key(password, salt, depth), block_size, True)


# uses a pre-generated key to encrypt data
def enc_from_key(text, key, block_size=_default_block_size_):
    return _encrypter_(True, text, key, block_size, True)


# decrypts data
def dec_from_pass(e_text, password, salt, depth=_default_pass_depth_, block_size=_default_block_size_):
    return _encrypter_(False, e_text, pass_to_key(password, salt, depth), block_size, True)


# uses a pre-generated key to decrypt data
def dec_from_key(e_text, key, block_size=_default_block_size_):
    return _encrypter_(False, e_text, key, block_size, True)


# encrypts a file
def enc_file_from_pass(file, password, salt, file_output, depth=_default_pass_depth_, compressor=False):
    return _file_encrypter_(True, file, pass_to_key(password, salt, depth), file_output, compressor)


# decrypts a file
def dec_file_from_pass(e_file, password, salt, file_output, depth=_default_pass_depth_, compressor=False):
    return _file_encrypter_(False, e_file, pass_to_key(password, salt, depth), file_output, compressor)


# rounds dt to an amount of seconds
# this function can be used to create a time based key system
def round_time(dt=None, round_to=30):
    if not dt:
        dt = _datetime_.now()
    seconds = (dt.replace(tzinfo=None)-dt.min).seconds
    return dt+_timedelta_(0, (seconds+round_to/2)//round_to*round_to-seconds, -dt.microsecond)


# hashes a file using the SHA512 algorithm
def hash_a_file(file):
    hash_ = _sha512_()
    with open(file, 'rb') as hash_file:
        buf = hash_file.read(262144)
        while len(buf) > 0:
            hash_.update(buf)
            buf = hash_file.read(262144)
    return to_base(17, 95, hash_.hexdigest())
