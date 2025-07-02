from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

print(os.environ['OPENAI_API_KEY'])

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
res = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "로맨틱한 분위기란?"}]
)
print(res.choices[0].message.content)