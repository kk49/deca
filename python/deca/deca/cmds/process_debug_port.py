from deca.file import ArchiveFile
import socket

ip = '10.0.0.16'
port = 9200

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))

with ArchiveFile(s.makefile(mode='rwb')) as f:
    count = f.read_u32()
    while count is not None:
        if count > 4:
            flag = f.read_u8()
            if flag == 0:
                objid = f.read_u64()
                param = objid & 0xFFFF
                objid = objid >> 16
                cnt = f.read_u32()
                scripts = []
                for i in range(cnt):
                    scnt1 = f.read_u32()
                    id1 = f.read(scnt1)
                    scripts.append(id1)
                loca_size = f.read_u32()
                loca = f.read(loca_size)
                print('msg{:02x}: {} 0x{:012X} {} {} {} {}'.format(flag, count, objid, param, cnt, scripts, loca))
            elif flag == 1:
                objid = f.read_u64()
                param = objid & 0xFFFF
                objid = objid >> 16
                print('msg{:02x} {} 0x{:012X} {}'.format(flag, count, objid, param))
            else:
                buffer = f.read(count - 5)
                print('msg{:02x}: {} {}'.format(flag, count, buffer))
        count = f.read_u32()

