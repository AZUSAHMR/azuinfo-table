from flask import Flask
from flask import Response
from flask import request
from flask import abort
from flask import send_file
import json
import time
import os
import string
import random
import requests
from io import BytesIO
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

CDN = "CDNDIR"

def randomString():
	return "".join(random.choice(string.ascii_uppercase+string.digits) for _ in range(6))

def calc(font,txt,width=0,height=0,x=0,y=0):
	size = font.getsize(txt)
	offset = font.getoffset(txt)

	return ((width-size[0]-offset[0])/2+x,(width-size[1]-offset[1])/2+y)

def marker(clear):
	if clear==1:
		return (0,221,170)
	elif clear==2:
		return (170,0,221)
	elif clear==3:
		return (255,136,170)
	elif clear==4:
		return (255,255,153)

app = Flask(__name__)

@app.route("/")
def index():
	return send_file("index.html")

@app.route("/save",methods=["POST"])
def save():
	data = json.loads(request.data.decode("UTF-8"))

	if "size" not in data:
		abort(500)
	if "x" not in data["size"]:
		abort(500)
	if "y" not in data["size"]:
		abort(500)
	if "data" not in data:
		abort(500)
	if int(data["size"]["x"])>=100:
		abort(500)
	if int(data["size"]["y"])>=100:
		abort(500)

	code = randomString()

	while os.path.exists("%s/sdvx/table/%s.json" % (CDN,code)):
		code = randomString()

	fp = open("%s/sdvx/table/%s.json" % (CDN,code) ,"w")
	fp.write(json.dumps(data))
	fp.close()

	return Response(code)

@app.route("/render/<code>/<nickname>.png")
def render(code,nickname):
	try:
		with open("%s/sdvx/table/%s.json" % (CDN,code)) as fp:
			data = json.load(fp)
	except:
		abort(404)

	req = requests.get("http://api.kano.kr/metadata/sdvx.json")
	metadata = req.json()["data"]

	req = requests.get("http://api.kano.kr/playdata/sdvx/%s.json" % nickname)
	userdata = req.json()

	if userdata["resCode"]!=0:
		abort(404)

	x = int(data["size"]["x"])
	y = int(data["size"]["y"])

	font = [ImageFont.truetype("RobotoMono-Bold.ttf",180),ImageFont.truetype("RobotoMono-Bold.ttf",140),ImageFont.truetype("RobotoMono-Bold.ttf",100),ImageFont.truetype("RobotoMono-Bold.ttf",80),ImageFont.truetype("RobotoMono-Bold.ttf",50),ImageFont.truetype("RobotoMono-Bold.ttf",25)]
	rgb = {"nov": (139,0,139), "adv": (255,215,0), "exh": (220,20,60), "mxm": (246,243,252), "inf": (0,206,209), "grv": (210,105,30), "hvn": (23,164,255)}

	size = [0,0]
	done = [0,0]
	txt = ["http://sdvx.azu.kr/%s" % nickname,userdata["data"]["user"]["name"]]

	while True:
		if done[0]==2 and done[1]==2:
			break

		for i in range(2):
			if done[i]==0:
				size[i]+=10
			elif done[i]==1:
				size[i]-=1
			else:
				continue

			tmp = ImageFont.truetype("RobotoMono-Bold.ttf",size[i])
			
			if done[i]==0 and (tmp.getsize(txt[i])[0]-tmp.getoffset(txt[i])[0])>(210*x*0.28):
				done[i] = 1
			elif done[i]==1 and (tmp.getsize(txt[i])[0]-tmp.getoffset(txt[i])[0])<=(210*x*0.28):
				done[i] = 2

	headerFont = [ImageFont.truetype("RobotoMono-Bold.ttf",size[0]),ImageFont.truetype("RobotoMono-Bold.ttf",size[1])]
	height = headerFont[0].getsize(txt[0])[1]-headerFont[0].getoffset(txt[0])[1]
	header = height*3+10*2
	header2 = headerFont[1].getsize(txt[1])[1]-headerFont[1].getoffset(txt[1])[1]

	if header2>header:
		header = header2

	header+=100

	im = Image.new("RGB",(210*x,240*y+header),"white")
	draw = ImageDraw.Draw(im)

	draw.text((calc(headerFont[1],userdata["data"]["user"]["name"],210*x)[0],10),userdata["data"]["user"]["name"],font=headerFont[1],fill=(0,0,0))

	draw.text((10,10),txt[0],font=headerFont[0],fill=(0,0,0))

	now = time.localtime()
	draw.text((10,10+height+10),"%04d-%02d-%02d %02d:%02d:%02d" % (now.tm_year,now.tm_mon,now.tm_mday,now.tm_hour,now.tm_min,now.tm_sec),font=headerFont[0],fill=(0,0,0))

	draw.text((10,10+height*2+10*2),code,font=headerFont[0],fill=(0,0,0))

	tmp = Image.open("azu.png")
	target = tmp.resize((header-20,header-20),Image.ANTIALIAS)
	tmp.close()
	im.paste(target,(210*x-header+20,0))

	draw.line((10,header-8,210*x-10,header-8),fill=(0,0,0),width=2)

	for i in range(y):
		for j in range(x):
			target = "%d_%d" % (i,j)
			base = (j*210,i*240+header)

			if data["data"][target]["diff"]!="nop":
				draw.line((base[0],base[1]+2.5,base[0]+197-2.5,base[1]+2.5),fill=rgb[data["data"][target]["diff"]],width=5)
				draw.line((base[0]+2.5,base[1],base[0]+2.5,base[1]+197-2.5),fill=rgb[data["data"][target]["diff"]],width=5)
				draw.line((base[0]+197-2.5,base[1]+197-2.5,base[0],base[1]+197-2.5),fill=rgb[data["data"][target]["diff"]],width=5)
				draw.line((base[0]+197-2.5,base[1]+197-1,base[0]+197-2.5,base[1]),fill=rgb[data["data"][target]["diff"]],width=5)

			if data["data"][target]["diff"]=="grv" or data["data"][target]["diff"]=="hvn":
				data["data"][target]["diff"]="inf"

			if "song" in data["data"][target]:
				img = Image.open("%s%s" % (CDN,metadata[data["data"][target]["song"]]["albumart_%s" % data["data"][target]["diff"]]))
				im.paste(img,(base[0]+5,base[1]+5))
				img.close()

			if "text" in data["data"][target]:
				draw.text(calc(font[len(data["data"][target]["text"])],data["data"][target]["text"],187,187,base[0]+5,base[1]+5),data["data"][target]["text"],font=font[len(data["data"][target]["text"])],fill=(0,0,0))

			try:
				rank = userdata["data"]["song"][data["data"][target]["song"]][data["data"][target]["diff"]]["rank"]
				
				if rank==4 or rank==6 or rank>=8:
					img = Image.open("%d.png" % rank)
				else:
					img = Image.open("%d.jpg" % rank)
					
				im.paste(img,(base[0],base[1]+202))
				img.close()

				score = str(userdata["data"]["song"][data["data"][target]["song"]][data["data"][target]["diff"]]["score"])

				size = font[5].getsize(score)
				offset = font[5].getoffset(score)

				draw.text((base[0]+197-size[0]-offset[0],base[1]+202-offset[1]),score,font=font[5],fill=(0,0,0))

				if userdata["data"]["song"][data["data"][target]["song"]][data["data"][target]["diff"]]["clear"]!=0:
					draw.line((base[0],base[1],base[0]+197,base[1]+197),fill=marker(userdata["data"]["song"][data["data"][target]["song"]][data["data"][target]["diff"]]["clear"]),width=18)
					draw.line((base[0]+197,base[1],base[0],base[1]+197),fill=marker(userdata["data"]["song"][data["data"][target]["song"]][data["data"][target]["diff"]]["clear"]),width=18)

			except:
				pass

	try:
		perc = int(request.args.get("perc"))
	except:
		perc = 100

	if perc<100 and perc>0:
		im = im.resize((int(210*x/100*perc),int((240*y+header)/100*perc)),Image.ANTIALIAS)

	buf = BytesIO()
	im.save(buf,"PNG")
	contents = buf.getvalue()
	im.close()
	buf.close()

	return Response(contents,mimetype="image/png")

if __name__ == "__main__":
	app.run(host="0.0.0.0",debug=True,port=5000,threaded=True)
