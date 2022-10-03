echo Setting up repository
        git clone --filter=blob:none --no-checkout --depth 1 --sparse https://github.com/rapidslayer101/Rdisc-Kivy app/code
        cd app/code
        git config core.sparsecheckout true
        echo rdisc.py > .git/info/sparse-checkout
        echo rdisc_kv.py >> .git/info/sparse-checkout
        echo enclib.py >> .git/info/sparse-checkout
        echo venv.zip >> .git/info/sparse-checkout
        git checkout
        tar -xf venv.zip
        )