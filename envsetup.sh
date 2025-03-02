#!/bin/sh
if [ -d "env" ]
then
  echo "Python virtual env exists"
else
  python3.8 -m venv env
fi

echo "Present Directory: $PWD"
activate () {
    . `pwd`/env/bin/activate
}
activate

pip3 install -r requirements.txt

