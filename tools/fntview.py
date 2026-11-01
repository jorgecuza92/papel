import struct, numpy as np
def load(path):
    d=open(path,'rb').read()
    maxw,h,asc,depth,first,default,size,nbits,noff,nwid=struct.unpack('<HHHHIIIIII',d[4:36])
    bits=d[36:36+nbits]; p=36+nbits
    long_off = nbits>=0xFFDB
    al=4 if long_off else 2; p=(p+al-1)//al*al
    fmt='<%d%s'%(noff,'I' if long_off else 'H'); offs=struct.unpack(fmt,d[p:p+noff*al]); p+=noff*al
    widths=d[p:p+nwid]
    return dict(h=h,asc=asc,depth=depth,first=first,offs=offs,widths=widths,bits=bits,maxw=maxw)
def glyph(f,ch):
    i=ord(ch)-f['first']; w=f['widths'][i] if f['widths'] else f['maxw']; o=f['offs'][i] if f['offs'] else i*((w*f['h']+1)//2)
    n=w*f['h']; px=[]
    for k in range(n):
        b=f['bits'][o+k//2]; v=(b>>(4*(k%2)))&15; px.append((15-v)/15)
    return np.array(px).reshape(f['h'],w)
def render(f,text,fg=(0,0,0),bg=(240,236,232)):
    gs=[glyph(f,c) for c in text]; a=np.concatenate(gs,1)
    fg=np.array(fg,float); bg=np.array(bg,float)
    return (bg*(1-a[...,None])+fg*a[...,None]).round().astype('uint8')
