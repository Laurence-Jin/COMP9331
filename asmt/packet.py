import struct

def unpack_helper(fmt, data):
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, data[:size]), data[size:]

with open("credentials.txt", "r") as fp:
    lines = fp.readlines()
    for line in lines:
        username, password = line.split()
        username = bytes(username, 'utf-8') 
        data = struct.pack('{}s'.format(len(username)), username)
        info = struct.unpack('{}s'.format(len(data)), data)
        ac = bytes("luke", 'utf-8')
        print(info[0])
        if info[0] == ac:
            print("1111")
        #print(info)

        
