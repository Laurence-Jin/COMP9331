from socket import *
import sys, pickle, time, os
import threading

client_username = " " #store for this client's name
time_out = 0 #also store the timeout for inactivity

#a class to operate it and store the socket address etc
class Client:
    def __init__(self, host, port):
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.host = host
        self.port = port
        self.server_addr = (host, port)

    #connect to server socket also check whether it is alive 
    def connection(self):
        try:
            self.client_socket.settimeout(0.01)
            self.client_socket.connect(self.server_addr)
        except timeout:
            print("You disconnected with server and timeout")
            os._exit(1)

    #for login process
    def login(self, data_set):
        print("Start to connect with server")
        login_success = False 
        username_requested = True #The step for inputting username
        
        while True:
            if login_success == False:
                if username_requested == True:
                    username = input("Username: ")
                    global client_username
                    client_username = username
                    data_set["username"] = username
                    data_set["method"] = "login"
                    #pickle convert the dict into byte format
                    self.client_socket.sendall(pickle.dumps(data_set))

                #if not recv the data more than little sec it means server stop connect and timeout
                try:
                    self.client_socket.settimeout(0.1)
                    data = self.client_socket.recv(1024) 
                    recv_data = pickle.loads(data)  
                    global time_out
                    time_out = recv_data["time_out"]
                except timeout:
                    print("You disconnected with server and timeout") 
                    os._exit(1) #terminate the terminal directly

                #after 3 attempt invalid input, the client send back
                if recv_data["message"] == "block":
                    print("Invalid Password. Your account has been blocked. Please try again later")
                    data_set["method"] = "logout"
                    self.client_socket.sendall(pickle.dumps(data_set))
                    self.client_socket.close()
                    os._exit(1)

                #if 3 attemps invalid password occur the server will send have block msg continuously until the time is up
                if recv_data["message"] == "have_blocked":
                    print("Your account is blocked due to multiple login failures. Please try again later")
                    data_set["method"] = "logout"
                    self.client_socket.sendall(pickle.dumps(data_set))
                    self.client_socket.close()
                    os._exit(1)

                if recv_data["message"] == "password_request":
                    recv_data["method"] = "password"
                    recv_data["message"] = input("Password: ")
                    self.client_socket.sendall(pickle.dumps(recv_data))

                    try:
                        self.client_socket.settimeout(0.1)
                        self.client_socket.sendall(pickle.dumps(recv_data))
                        data = self.client_socket.recv(1024)
                        recv_data = pickle.loads(data)
                    except timeout:
                        print("You disconnected with server and timeout")
                        os._exit(1)
                            
                if recv_data["message"] == "login_success":
                    login_success = True
                    print("Welcome to the greatest messaging application ever!")
                    return 1

                if recv_data["message"] == "new_user":
                    login_success = True
                    input("This is a new user. Enter a password: ")
                    print("Welcome to the greatest messaging application ever!")
                    return 1

                if recv_data["message"] == "invalid_password":
                    print("Invalid Password. Please try again")
                    recv_data["method"] = "password"
                    recv_data["message"] = input("Password: ")
                    recv_data["request_time"] += 1
                    username_requested = False
                    self.client_socket.sendall(pickle.dumps(recv_data))

            #the loop wait for 0.3 each time in case send the msg when server not send
            time.sleep(0.3)
                    
    #There are two main stage after login, the one is to send message to server it will run in one thread
    def send_message(self, data_set):   
        while True:
            try:
                new_input = input()
                command = new_input.split()
                key_in = command[0]
            except IndexError:
                print("Error. Invalid command")
                break
                
            if key_in == "whoelse":
                data_set["method"] = "whoelse"
                data_set["message"] = ""
                self.client_socket.sendall(pickle.dumps(data_set))
                try:
                    self.client_socket.settimeout(0.1)
                    data = self.client_socket.recv(1024)
                except timeout:
                    print("You disconnected with server and timeout.")
                    os._exit(1)
             
                recv_data = pickle.loads(data)
                List = recv_data["message"].split()
                rm_dup_list = list(dict.fromkeys(List))
                for user in rm_dup_list:
                    if user != client_username:
                        print(user)

            elif key_in == "broadcast":
                data_set["method"] = "broadcast"
                data_set["message"] = new_input
                self.client_socket.sendall(pickle.dumps(data_set))

            elif key_in == "message":
                data_set["method"] = "message"
                data_set["message"] = new_input
                self.client_socket.sendall(pickle.dumps(data_set))      

            elif key_in == "logout":
                data_set["method"] = "logout"
                self.client_socket.sendall(pickle.dumps(data_set))
                os._exit(1)
                
            else:
                print("Error. Invalid command")

            time.sleep(0.3)
            
    #This is another thread to receive msg for making sure run it synchronous 
    def recv_message(self):
        while True:
            global time_out
            try:
                self.client_socket.settimeout(time_out)
                data = self.client_socket.recv(1024)
                recv_data = pickle.loads(data)
            except timeout:
                print("You disconnected with server and timeout.")
                os._exit(1)            
            time_out = recv_data["time_out"]
            message_send = ''
            i = 0      
            if (recv_data["method"] == "Invalid_user"):
                    print("Error. Invalid user")

            if (recv_data["method"] == "send_from_others" or recv_data["method"] == "broadcast_to_all"): 
                for data in recv_data["message"].split():
                    if i == 0:
                        message_send = data+":"
                        i+= 1
                    elif data == "broadcast" or data == "message" or data == client_username:
                        pass
                    else:
                        message_send += " "+data
                print(message_send) 
            time.sleep(0.3)  
          

    def run(self):    
        data_set = {
            "method" : None, #method is to make sure the exact func which is header
            "username" : None,
            "message" : None, #msg sent, content
            "request_time" : 1,
            "time_out" : 0
        }   
        #if login success, it will return 1
        if self.login(data_set) == 1:
            while True:
                #two thread for run it synchronous or recv() in socket will stuck until rece the msg
                threading.Thread(target=self.recv_message).start()
                threading.Thread(target=self.send_message(data_set)).start()
                               
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\n===== Error usage, CLIENT_PORT ======\n")
        exit(0)
    
    server_host = "127.0.0.1"
    server_port = int(sys.argv[1])

    client = Client(server_host, server_port)
    client.connection()
    client.run()
    client.client_socket.close()