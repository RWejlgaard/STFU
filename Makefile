default: build

build:
	pip3 install -r ./requirements.txt
	~/Library/Python/3.9/bin/cython main.py --embed
	gcc -v -Os -I /usr/local/Frameworks/Python.framework/Versions/3.9/include/python3.9 -L /usr/local/Frameworks/Python.framework/Versions/3.9/lib -o stfu main.c  -lpython3.9  -lpthread -lm -lutil -ldl

install:
	cp ./stfu /usr/local/bin/stfu

clean:
	rm main.c stfu