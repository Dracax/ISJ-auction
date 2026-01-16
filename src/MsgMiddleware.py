# TODO: Listen for all Messages (uni, multi, broad)
from server import Server


def listenForMessage(data):

    myServer: Server # TODO:maybe wrong

    # start as thread
    # All on the same port, but individual sockets
    # socket uni listen_socket.receive_data()
    # socket multi listen_socket.receive_data()
    # socket broad listen_socket.receive_data()
    # check Data for correctness etc etc


    myServer.receive_message(data.abstractDataMessage)

    return