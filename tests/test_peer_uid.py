import os
import socket
import struct

import pytest


@pytest.mark.skipif(not hasattr(socket, "SO_PEERCRED"), reason="SO_PEERCRED not supported")
def test_peercred_local_socket():
    s1, s2 = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        ucred = s1.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, gid = struct.unpack("3i", ucred)
        assert uid == os.geteuid()
        assert gid == os.getegid()
        assert pid > 0
    finally:
        s1.close()
        s2.close()
