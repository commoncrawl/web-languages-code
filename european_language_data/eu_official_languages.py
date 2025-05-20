from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

filename = "eu_official_languages_with_iso639_3.csv"

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.setReturnFormat(JSON)
sparql.addCustomHttpHeader("User-Agent", "CCF-Official-EU-Langs/1.0")

sparql.setQuery("""
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>

SELECT DISTINCT ?language ?languageLabel ?iso639_3
WHERE {
  wd:Q458 wdt:P37 ?language.       # Q458 = European Union
  OPTIONAL { ?language wdt:P220 ?iso639_3. }  # ISO 639-3 code
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""")
# ORDER BY ?iso639_3

results = sparql.query().convert()

data = []
for r in results["results"]["bindings"]:
    label = r["languageLabel"]["value"]
    iso639_3 = r["iso639_3"]["value"] if "iso639_3" in r else None

    # Ancient Greek isn't an official EU language, is it
    if label == "Greek" and iso639_3 is None:
        iso639_3 = "ell"

    data.append({
        "iso639_3": iso639_3,
        "lang": label,
        "wikidataurl": r["language"]["value"]
    })

df = pd.DataFrame(data)
df = df.sort_values("iso639_3")
df.to_csv(filename, index=False)
print(f"Saved to {filename}")
