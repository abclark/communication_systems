def calculate_checksum(data):
    if len(data) % 2 == 1:
        data += b'\x00'
        
    s = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i+1]
        s += word
        
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
        
    checksum = ~s & 0xFFFF
    
    return checksum
