"""
Fetches a real sample of providers from the NPPES API and generates
a synthetic provider directory + claims feed with realistic errors baked in.
All synthetic data — no PHI.
"""
import requests, csv, random, time
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)
RAW = "data/raw"

# The NPPES API needs more than just 'state' to return results.
# We query (city, state) pairs across big metros to get real variety.
CITY_STATE = [
    ("New York", "NY"), ("Brooklyn", "NY"),
    ("Los Angeles", "CA"), ("San Diego", "CA"),
    ("Houston", "TX"), ("Dallas", "TX"),
    ("Chicago", "IL"),
    ("Miami", "FL"), ("Orlando", "FL"),
]

def fetch_real_providers():
    providers = []
    for city, st in CITY_STATE:
        params = {
            "version": "2.1",
            "city": city,
            "state": st,
            "enumeration_type": "NPI-1",
            "limit": 40,
        }
        try:
            r = requests.get("https://npiregistry.cms.hhs.gov/api/",
                             params=params, timeout=30)
            results = r.json().get("results", [])
            print(f"  {city}, {st}: {len(results)} providers")
            for res in results:
                basic = res.get("basic", {})
                # find the practice-location address
                addr = {}
                for a in res.get("addresses", []):
                    if a.get("address_purpose") == "LOCATION":
                        addr = a; break
                if not addr and res.get("addresses"):
                    addr = res["addresses"][0]
                npi = str(res.get("number", ""))
                fn = basic.get("first_name", "")
                ln = basic.get("last_name", "")
                if npi and fn and ln:
                    providers.append({
                        "npi": npi,
                        "first_name": fn,
                        "last_name": ln,
                        "city": addr.get("city", city),
                        "state": addr.get("state", st),
                        "postal_code": (addr.get("postal_code", "") or "")[:5],
                    })
            time.sleep(0.3)  # be polite to the public API
        except Exception as e:
            print(f"  warning: {city},{st} failed ({e})")
    # de-duplicate by NPI
    seen, unique = set(), []
    for p in providers:
        if p["npi"] not in seen:
            seen.add(p["npi"]); unique.append(p)
    return unique

print("Fetching real providers from NPPES API...")
real = fetch_real_providers()
print(f"  got {len(real)} unique real providers")

if len(real) < 20:
    raise SystemExit("Got too few providers — stopping so we can debug the API call.")

with open(f"{RAW}/nppes_providers.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["npi","first_name","last_name","city","state","postal_code"])
    w.writeheader(); w.writerows(real)

# ---- synthetic DIRECTORY with injected errors ----
directory = []
for i, p in enumerate(real):
    directory.append({
        "directory_id": f"DIR{i:05d}",
        "npi": p["npi"],
        "first_name": p["first_name"],
        "last_name": p["last_name"],
        "address": fake.street_address(),
        "city": p["city"],
        "state": p["state"],
        "zip": p["postal_code"],
        "phone": fake.numerify("###-###-####"),
        "accepting_new_patients": random.choice(["Y","N"]),
    })

n = len(directory)
for rec in random.sample(directory, k=max(1,int(n*0.10))):
    rec["npi"] = fake.numerify("##########")        # fake NPI
for rec in random.sample(directory, k=max(1,int(n*0.08))):
    rec["state"] = random.choice(["WA","AZ","OH","GA"])  # wrong state
for rec in random.sample(directory, k=max(1,int(n*0.07))):
    rec["phone"] = ""                                # missing phone
for d in random.sample(directory, k=max(1,int(n*0.05))):
    copy = dict(d); copy["directory_id"] = d["directory_id"]+"_DUP"
    directory.append(copy)                           # duplicate
random.shuffle(directory)

with open(f"{RAW}/provider_directory.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(directory[0].keys()))
    w.writeheader(); w.writerows(directory)
print(f"  built directory with {len(directory)} listings (errors injected)")

# ---- synthetic CLAIMS feed (75% of providers active; rest are 'ghosts') ----
claims = []
active = random.sample(real, k=int(len(real)*0.75))
for p in active:
    for _ in range(random.randint(1,20)):
        claims.append({
            "claim_id": fake.uuid4(),
            "npi": p["npi"],
            "service_date": fake.date_between(start_date="-1y").isoformat(),
            "claim_amount": round(random.uniform(80,4000),2),
        })
random.shuffle(claims)
with open(f"{RAW}/claims.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["claim_id","npi","service_date","claim_amount"])
    w.writeheader(); w.writerows(claims)
print(f"  built {len(claims)} claims for {len(active)} active providers")
print("\nDone — files in data/raw/")
