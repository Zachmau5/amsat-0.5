from urllib.request import Request, urlopen

def fetch_and_save_tle(url, filename):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urlopen(req) as response:
            data = response.read().decode('utf-8')
        with open(filename, 'w') as f:
            f.write(data)
        print(f"[✅] TLE data saved to {filename}")
    except Exception as e:
        print(f"[❌] Failed to fetch TLE data: {e}")

if __name__ == "__main__":
    fetch_and_save_tle(
        "https://www.celestrak.com/NORAD/elements/amateur.txt",
        "amateur.tle"
    )
