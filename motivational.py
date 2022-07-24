from dotenv import load_dotenv
from flask import Flask
from flask import request as flrq
from twilio.twiml.messaging_response import MessagingResponse 
from textblob import TextBlob
from random import randint
import asyncio, aiohttp, os, json
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()
motkn = os.environ['GIPHY_MOTIVATIONAL']
url = "https://api.giphy.com/v1/gifs/translate?api_key={}&s={}&weirdness={}&limit={}" #gif url
qurl = 'https://zenquotes.io/api/random/' #quotes url
durl = 'https://zenquotes.io/api/today/' #today's quote
app = Flask(__name__)


async def gif_get(client, qry):
    async with client.get(url.format(motkn, qry, randint(0, 7), 1)) as gif_rsp:
        gif_id = json.loads(await gif_rsp.text())['data']['id']
    return f"https://media.giphy.com/media/{gif_id}/giphy.gif"


async def qot_get(client, stmt):
    if stmt < 0:
        async with client.get(qurl) as qot_rsp:
            base = json.loads(await qot_rsp.text())
            quote = base[0]['q']
            author = base[0]['a']
        return f"I'm sorry you feel that way. As parting advice, {author} once said '{quote}'"
    elif stmt > 0:
        async with client.get(durl) as qot_rsp:
            base = json.loads(await qot_rsp.text())
            quote = base[0]['q']
            author = base[0]['a']
        return f"I'm glad that you feel good today. Here's something to ponder on: {author} once said '{quote}'"


async def all_api(qry, stmt):
    async with aiohttp.ClientSession() as client:
        gif_string = await gif_get(client, qry)
        quote_string = await qot_get(client, stmt)
    return gif_string, quote_string

async def gif_only():
    async with aiohttp.ClientSession() as client:
        gif_string = await gif_get(client, "cute animal")
    return gif_string

@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    # Start TwiML response
    resp = MessagingResponse()
    try:
        #parse body and get sentiment:
        data = flrq.get_data().decode('utf-8')
        data = data.split('&')
        data = data[10].split('=')[1].lower().replace('+', ' ')
        sms_sentiment = TextBlob(data).sentiment[0]

        if sms_sentiment < 0:
            gif_s, qot_s = asyncio.run(all_api(qry="daily motivational gif", stmt=sms_sentiment))
            msg = resp.message(qot_s)
            msg.media(gif_s)
            return str(resp)
        
        elif sms_sentiment > 0:
            gif_s, qot_s = asyncio.run(all_api(qry="live in the moment", stmt=sms_sentiment))
            msg = resp.message(qot_s)
            msg.media(gif_s)
            return str(resp)
        
        else:
            gif_s = asyncio.run(gif_only())
            msg = resp.message("I can't tell how you're feeling. Here's a cute animal instead")
            msg.media(gif_s)
            return str(resp)

        
    except Exception as e:
        print(e)
        msg = resp.message("looks like something is going wrong. This is fine :)")
        msg.media(
            "https://media.giphy.com/media/z9AUvhAEiXOqA/giphy.gif"
        )
        return str(resp)
        
        
if __name__ == "__main__":
    app.run(debug=True)