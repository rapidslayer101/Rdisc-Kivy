if EXIST launch.bat (
    echo "launch.bat already exists, skipping installation"
    start launch.bat
) ELSE (
    echo Setting up repository
    git clone --filter=blob:none --no-checkout --depth 1 --sparse https://github.com/rapidslayer101/Rdisc-Kivy
    cd Rdisc
    git config core.sparsecheckout true
    echo venv.zip > .git/info/sparse-checkout
    echo rdisc.py >> .git/info/sparse-checkout
    echo rdisc_kv.py >> .git/info/sparse-checkout
    echo enclib.py >> .git/info/sparse-checkout
    echo requirements.txt >> .git/info/sparse-checkout
    echo launch.bat >> .git/info/sparse-checkout
    echo Downloading and unpacking files
    git checkout
    tar -xf venv.zip
    cd venv/Scripts
    pip.exe install -r requirements.txt
    cd ..
    echo Starting client
    start python.exe rdisc.py
)