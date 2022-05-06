import socket
from os import scandir, path, mkdir, remove
from hashlib import sha1
from math import ceil
hname_lookup = {
    "{SERVER IP}":"{CLIENT IP}",
    "{CLIENT IP}":"{SERVER IP}"
}
BUFFSIZE = 64*1024
def get_details(fpath):
    if isinstance(fpath,str):
        fpath = fpath.encode("utf-8")
    def scan(fpath):
        if path.isfile(fpath):
            return tuple(), (fpath,)
        dirpaths = [fpath]
        directories = []
        files = []
        while len(dirpaths) != 0:
            rtrnpaths = []
            for fpath in dirpaths:
                with scandir(fpath) as direntry:
                    for file in direntry:
                        abs_fpath = fpath + b'/' + file.name
                        if file.is_dir():
                            rtrnpaths.append(abs_fpath)
                            directories.append(abs_fpath)
                        else:
                            files.append(abs_fpath)
            dirpaths = rtrnpaths
        return tuple(directories), tuple(files)
    def get_sizes_bytes(files):
        rtrnlist = []
        for fpath in files:
            rtrnlist.append((fpath, path.getsize(fpath)))
        return tuple(rtrnlist)
    directories, files = scan(fpath)
    files = get_sizes_bytes(files)
    return directories, files
def as_client(send_directories,send_files):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hname_lookup[socket.gethostbyname(socket.gethostname())], 5431))
    print("Connected to server...")
    def split_str(bstrobj):
        while len(bstrobj) > BUFFSIZE:
            yield bstrobj[0:BUFFSIZE]
            bstrobj = bstrobj[BUFFSIZE:]
        yield bstrobj
    def send_file(fpath):
        s.send(fpath[1])
        s.recv(8)
        with open(fpath[0],'rb') as rf:
            data = rf.read(BUFFSIZE)
            while data is not None:
                s.send(data)
                s.recv(8)
                data = rf.read(BUFFSIZE)
    def transfer(directory_paths, file_paths):
        def transfer_directories(directory_paths):
            print(f"Transfering {len(directory_paths)} directories...")
            s.send(b'\x01')
            s.recv(8)
            s.send(len(directory_paths))
            s.recv(8)
            for dirpath in directory_paths:
                for fname_chunk in split_str(dirpath):
                    s.send(fname_chunk)
                    s.recv(8)
        def transfer_files(file_paths):
            print(f"Transfering {len(file_paths)} files...")
            s.send(b'\x01')
            s.recv(8)
            s.send(len(file_paths))
            s.recv(8)
            for fname in file_paths:
                for fname_chunk in split_str(fname[0]):
                    s.send(fname_chunk)
                    s.recv(8)
                send_file(fname)
        transfer_directories(directory_paths)
        transfer_files(file_paths)
    transfer(send_directories,send_files)
    s.close()
def as_server_receive():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((socket.gethostbyname(socket.gethostname()), 5431))
    s.listen()
    conn, addr = s.accept()
    print(f"Accepted connection from {addr}")
    def recieve_directories():
        val = conn.recv(8)
        if val != b'\x01':
            conn.close()
        conn.send(b'\x01')
        number_of_directories = int.from_bytes(conn.recv(BUFFSIZE),"big")
        checked = {}
        conn.send(b'\x01')
        for _ in range(number_of_directories):
            dir_path = [conn.recv(BUFFSIZE)]
            while len(dir_path[-1]) > BUFFSIZE:
                conn.send(b'\x01')
                dir_path.append(conn.recv(BUFFSIZE))
            dir_path = b''.join(dir_path)
            mk_paths = [dir_path]
            res = dir_path.rfind(b'/')
            while res != -1:
                next_res = dir_path.rfind(b'/',0,res)
                if next_res == -1 or dir_path[0:res] in checked:
                    break
                else:
                    checked[dir_path[0:res]] = None
                    mk_paths.append(dir_path[0:res])
                res = next_res
            for mk_path in mk_paths[::-1]:
                if path.exists(mk_path):
                    if path.isfile(mk_path):
                        remove(mk_path)
                        mkdir(mk_path)
                else:
                    mkdir(mk_path)
                checked[mk_path] = None
            conn.send(b'\x01')
    def receive_file():
        data = conn.recv(BUFFSIZE)
        fpath = data[8:]
        fsize = int.from_bytes(data[0:8],'big')
        count = 0
        with open(fpath,'wb') as wf:
            l = 1
            conn.send(b'\x01')
            while(l):
                l = conn.recv(BUFFSIZE)
                while (l):
                    wf.write(l)
                    l = conn.recv(BUFFSIZE)
    def recieve_files():
        print("Recieving fileconn...")
        val = conn.recv(8)
        if val != b'\x01':
            conn.close()
        conn.send(b'\x01')
        number_of_files = int.from_bytes(conn.recv(BUFFSIZE),"big")
        conn.send(b'\x01')
        for _ in range(number_of_files):
            receive_file()
    recieve_directories()
    recieve_files()
    s.close()
directories, file_paths = get_details("{YOUR FILEPATH}")