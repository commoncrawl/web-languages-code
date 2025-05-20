from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

filename = "european_languages_full.csv"

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.setReturnFormat(JSON)
sparql.addCustomHttpHeader("User-Agent", "CCF-European-Langs/1.0")

# Get all official EU languages
sparql.setQuery("""
SELECT DISTINCT ?language
WHERE {
  wd:Q458 wdt:P37 ?language .
}
""")
eu_results = sparql.query().convert()
official_eu_langs = {r["language"]["value"] for r in eu_results["results"]["bindings"]}

# Get all languages used or official in Europe, with country Q-ID, label, ISO 639-3 code
sparql.setQuery("""
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>

SELECT DISTINCT ?language ?languageLabel ?iso639_3 ?iso639_1 ?speakers
                ?country ?countryLabel ?iso3166 ?officialUse
WHERE {
  ?country wdt:P31 wd:Q6256 ;
           wdt:P30 wd:Q46 .

  {
    ?country wdt:P37 ?language .
    BIND(true AS ?officialUse)
  }
  UNION
  {
    ?country wdt:P2936 ?language .
    BIND(false AS ?officialUse)
  }

  OPTIONAL { ?language wdt:P220 ?iso639_3. }
  OPTIONAL { ?language wdt:P218 ?iso639_1. }
  OPTIONAL { ?language wdt:P1098 ?speakers. }
  OPTIONAL { ?country wdt:P297 ?iso3166. }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?languageLabel
""")

results = sparql.query().convert()

rows = []
for r in results["results"]["bindings"]:
    lang = r["languageLabel"]["value"]
    lang_uri = r["language"]["value"]
    iso_3 = r.get("iso639_3", {}).get("value")
    iso_1 = r.get("iso639_1", {}).get("value")
    speakers = r.get("speakers", {}).get("value")
    country_uri = r["country"]["value"]
    country_label = r["countryLabel"]["value"]
    country_iso = r.get("iso3166", {}).get("value")  # canonical key
    is_official = r["officialUse"]["value"] == "true"

    if not iso_3:
        if "Sámi" in lang:
            iso_3 = "sme"
        elif lang == "Greek":
            iso_3 = "ell"
        elif lang == "Demotic Greek":
            continue

    if not country_iso:
        continue  # can't canonicalise this country

    rows.append({
        "language": lang,
        "lang_wikidataurl": lang_uri,
        "iso639_3": iso_3,
        "iso639_1": iso_1,
        "country_iso": country_iso,
        "country_label": country_label,
        "speakers": speakers,
        "official_EU_language": lang_uri in official_eu_langs,
        "is_official": is_official
    })

# dataframe + canonical country labels
df = pd.DataFrame(rows)
df = df[df["iso639_3"].notna()]
df["speakers"] = pd.to_numeric(df["speakers"], errors="coerce")

# canonical label for each country ISO
iso_to_label = df.groupby("country_iso")["country_label"].first().to_dict()
df["country"] = df["country_iso"].map(iso_to_label)

# group all countries (used or official)
group_all = (
    df.groupby(["language", "lang_wikidataurl", "iso639_3", "iso639_1", "official_EU_language"])
    .agg({
        "country": lambda x: ", ".join(sorted(set(x))),
        "speakers": "max"
    })
    .rename(columns={"country": "countries"})
)

# group only official countries
official_df = df[df["is_official"]]
group_official = (
    official_df.groupby(["language", "lang_wikidataurl", "iso639_3", "iso639_1", "official_EU_language"])
    .agg({
        "country": lambda x: ", ".join(sorted(set(x)))
    })
    .rename(columns={"country": "official_countries"})
)

# merge and save
final_df = group_all.merge(group_official, how="left", on=[
    "language", "lang_wikidataurl", "iso639_3", "iso639_1", "official_EU_language"
])

final_df.reset_index().to_csv(filename, index=False)
print(f"Saved to {filename}")
