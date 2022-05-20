from socket import *
from threading import Thread
import sys, time, pickle, errno

user_info = [] #core class list, to store each client's information a user per list
block_set = [] #if user try to login 3 times and invalid it will store this name in list
block_time = 0 #command input set for block time
time_out = 0 #command input set for  timeout

#This list is to store client's info
class User:
    def __init__(self, username, message, address, time):
        self.username = username
        self.message = message
        self.address = address
        self.time = time

#This class store the socket of server and run function catch the message sent by client and deal with it
class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        server_addr= (host, port)
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.bind(server_addr)
        self.clientAlive = False 
    
    def client_func(self, client_socket, client_addr):
        status = 0 #identifier for input the password
        username = "" #store this thread's username
        data_set = {} #data_set is the format or procotol we said sent through server and each client
        while self.clientAlive: 
            try:
                client_socket.settimeout(time_out)
                recv_data = client_socket.recv(1024)       
            except timeout:
                #if timeout for client inactivity, broadcast it has logged out to other clients 
                if len(data_set) != 0:
                    self.broadcast_log_out(data_set)                 
                if username != " ":          
                    self.log_out(username, client_addr) 
                sys.exit()    #server only need to exit this thread corresponding to one client  

            data_set = pickle.loads(recv_data)
            username, header = data_set["username"], data_set["method"]
            data_set["time_out"] = time_out #send timeout in server to client also execute settime in client

            if header == "logout":
                self.log_out(username, client_addr)
                #broadcast it has logged out to other clients
                self.broadcast_log_out(data_set)
                sys.exit()

            if header == "login":
                password_requested = self.check_username(data_set, client_socket)

            if header == "password":
                #status 1 -> success -1 -> not sucess mean password incorret
                status = self.check_password(data_set, client_socket, password_requested, client_addr)

            if header == "whoelse":
                self.check_other_user(data_set, client_socket)

            if header == "message":
                self.message_to_user(username, data_set, client_socket)

            if header == "broadcast":
                self.broadcast_to_all(username, data_set, client_socket)

            if password_requested == -1 and status == -1: 
                #occur in 3 times password error
                sys.exit()
        #set certain time in each thread run in case the receive error
        time.sleep(0.3)

    #presence notification to other client 
    def broadcast_log_out(self, data_set):
        username = data_set["username"]
        for user in user_info: 
            if user.username != username:
                data_set["method"] = "broadcast_to_all"
                data_set["message"] = username+" logged out"
                try:
                    user.address.send(pickle.dumps(data_set)) #send the specific username with its client socket
                except IOError as e:
                    if e.errno == errno.EPIPE:
                        print("pipe error")

    #show the addr in server and remove it from the user_info list in case affect whoelse
    def log_out(self, username, client_addr):
        self.clientAlive = False
        print("===== the user disconnected - ", client_addr)
        for user in user_info:
            if user.username == username:
                user_info.remove(user)

    #send message to other client
    def message_to_user(self, username, data_set, client_socket):
        msg = data_set["message"].split()
        for user in user_info:
            if user.username == msg[1]:
                data_set["method"] = "send_from_others"
                data_set["message"] = username+" "+data_set["message"]
                #send this wanted client's address for client to client
                user.address.send(pickle.dumps(data_set)) 
                return 

        #if server didnot search this client, then it will be invalid user and send it back to origin call's client
        data_set["method"] = "Invalid_user"
        client_socket.send(pickle.dumps(data_set))

    #broadcast to all other client excpet for itself
    def broadcast_to_all(self, username, data_set, client_socket):
        msg = username+" "+data_set["message"]
        for user in user_info: 
            if user.username != username:
                data_set["method"] = "broadcast_to_all"
                data_set["message"] = msg
                user.address.send(pickle.dumps(data_set))
                #send the specific username with its client socket

    #check whether other user exist as whoelse 
    def check_other_user(self, data_set, client_socket):
        msg = ""
        for user in user_info:
            if msg == None:
                msg = user.username
            else:
                msg += "\n"+user.username
        data_set["method"] = "whoelse"
        data_set["message"] = msg
        client_socket.send(pickle.dumps(data_set))

    #very first place to check the if this username store in txt or new user
    def check_username(self, data_set, client_socket):
        data_set["time_out"] = time_out
        for block in block_set:
            if block == data_set["username"]:
                message = "have_blocked"
                data_set["message"] = message
                client_socket.send(pickle.dumps(data_set))
                return -1

        with open("credentials.txt", "r") as fp:
            lines = fp.readlines()
            for line in lines:
                username, password = line.split()
                if data_set["username"] == username:
                    message = "password_request"
                    data_set["message"] = message
                    client_socket.send(pickle.dumps(data_set))
                    return password 
            #if not found in txt then it will be a new user and I need to store it in list array
            message = "new_user"
            data_set["message"] = message
            client_socket.send(pickle.dumps(data_set))
            new_user = User(data_set["username"], data_set["message"], client_socket, 0)
            user_info.append(new_user)
            return None

    #check the password with existed user
    def check_password(self, data_set, client_socket, password, client_addr):
        if data_set["message"] == password:   
            message = "login_success"
            data_set["message"] = message
            client_socket.send(pickle.dumps(data_set))
            new_user = User(data_set["username"], data_set["message"], client_socket, 0)
            user_info.append(new_user)
            return 1

        ##when this client blocks after 3 attemps error
        elif data_set['request_time'] == 3: 
            message = "block"
            print(message, client_addr)
            data_set["message"] = message
            client_socket.send(pickle.dumps(data_set))

            block_set.append(data_set["username"])
            time.sleep(block_time)
            block_set.remove(data_set["username"])
            return -1

        #if not 3 attempts then send invalid notification back to client
        else:
            message = "invalid_password"
            data_set["message"] = message
            client_socket.send(pickle.dumps(data_set))
            return 0

    #multi-thread with each client for speed up
    def accpet_thread_func(self):
        self.server_socket.listen(10)
        print("Server start listening!")

        while True:
            client_socket, client_addr = self.server_socket.accept()
            print("Server has received a new connection", client_addr)    
            self.clientAlive = True
            client_threading = Thread(target=self.client_func, args=(client_socket, client_addr))
            client_threading.setDaemon(True)
            client_threading.start()       

    def run(self):
        accept_threading = Thread(target=self.accpet_thread_func)
        accept_threading.setDaemon(True)
        accept_threading.start()
             
        while True:
            try:
                time.sleep(0.3)
            except KeyboardInterrupt:
                break
            
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("\n===== Error usage, SERVER_PORT ======\n")
        exit(0)
    
    server_host = "127.0.0.1" #local host
    server_port = int(sys.argv[1])
    block_time = int(sys.argv[2])
    time_out = int(sys.argv[3])

    server = Server(server_host, server_port)
    server.run()