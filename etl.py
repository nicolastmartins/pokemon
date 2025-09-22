import requests
import time
import pandas as pd

# ============================================================
# 1. Autenticação - obter JWT
# ============================================================
def get_jwt_token(base_url, username, password):
    url = f"{base_url}/login"
    payload = {"username": username, "password": password}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        token = response.json().get("access_token")
        print("Token JWT obtido com sucesso.")
        return token
    except Exception as e:
        print(f"Erro ao obter token JWT: {e}")
        return None


# ============================================================
# 2. Extração de Pokémons
# ============================================================
def extract_pokemons(base_url, token, per_page=50):
    url = f"{base_url}/pokemon"
    headers = {"Authorization": f"Bearer {token}"}

    all_pokemons = []
    page = 1

    try:
        # primeira chamada para pegar total de pokemons
        response = requests.get(url, headers=headers, params={"page": page, "per_page": per_page})
        response.raise_for_status()
        data = response.json()

        total = data.get("total", len(data.get("items", data.get("pokemons", []))))
        total_pages = (total // per_page) + (1 if total % per_page != 0 else 0)

        print(f"ℹ️ API reportou {total} pokémons. Calculado {total_pages} páginas.")

        all_pokemons.extend(data.get("items", data.get("pokemons", [])))

        # pegar o resto das páginas
        for page in range(2, total_pages + 1):
            time.sleep(0.8)
            print(f"Buscando página {page}/{total_pages}...")

            for tentativa in range(3):  # até 3 tentativas
                response = requests.get(url, headers=headers, params={"page": page, "per_page": per_page})
                if response.status_code == 429:
                    espera = 2 ** tentativa
                    print(f"Rate limit na página {page}, aguardando {espera}s...")
                    time.sleep(espera)
                    continue
                response.raise_for_status()
                data = response.json()
                all_pokemons.extend(data.get("items", data.get("pokemons", [])))
                break

        print(f"Extração completa: {len(all_pokemons)} pokémons obtidos.")
        return all_pokemons

    except Exception as e:
        print(f"Falha ao buscar pokémons: {e}")
        return []


# ============================================================
# 3. Extração de Combates
# ============================================================
def extract_combats(base_url, token, per_page=10):
    all_combats = []
    page = 1

    while True:
        url = f"{base_url}/combats"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"page": page, "per_page": per_page}

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Falha ao buscar combates na página {page}: {response.status_code}")
            break

        data = response.json()
        combats = data.get("combats", [])
        all_combats.extend(combats)

        total = data.get("total", 0)
        if page * per_page >= total or not combats:
            break
        page += 1
        time.sleep(0.5)

    print(f"Extração completa: {len(all_combats)} combates obtidos.")
    return all_combats


# ============================================================
# 4. Extração de Status dos Pokémons
# ============================================================
def extract_pokemon_details(base_url, token, pokemons_data):
    headers = {"Authorization": f"Bearer {token}"}
    detalhes_list = []

    total = len(pokemons_data)
    for idx, p in enumerate(pokemons_data, start=1):
        pokemon_id = p['id']
        url = f"{base_url}/pokemon/{pokemon_id}"

        for tentativa in range(3):
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 429:
                    espera = 2 ** tentativa
                    print(f"Rate limit no Pokémon {pokemon_id}, aguardando {espera}s...")
                    time.sleep(espera)
                    continue
                response.raise_for_status()
                detalhes_list.append(response.json())
                break
            except Exception as e:
                print(f" Erro ao buscar detalhes do Pokémon {pokemon_id}: {e}")
                time.sleep(1)

        # Mostrar progresso
        print(f"ℹ️ {idx}/{total} Pokémons extraídos: {p['name']}")

    print(f" Extração completa: {len(detalhes_list)} Pokémon detalhados obtidos.")
    return detalhes_list


# ============================================================
# 5. Transformação e Carga
# ============================================================
def transform_and_load(combats_data, pokemons_data):
    print("\nIniciando fase de Transformação e Carga...")

    # 1. Converter para DataFrames
    df_combats = pd.DataFrame(combats_data)
    df_pokemons = pd.DataFrame(pokemons_data)

    # 2. Renomear colunas
    df_combats = df_combats.rename(
        columns={
            'first_pokemon': 'pokemon_1_id',
            'second_pokemon': 'pokemon_2_id',
            'winner': 'winner_id'
        }
    )
    df_pokemons_stats = df_pokemons.rename(columns={'id': 'pokemon_id'})

    # 3. Corrigir tipos
    df_combats['pokemon_1_id'] = df_combats['pokemon_1_id'].astype(int)
    df_combats['pokemon_2_id'] = df_combats['pokemon_2_id'].astype(int)
    df_combats['winner_id'] = df_combats['winner_id'].astype(int)
    df_pokemons_stats['pokemon_id'] = df_pokemons_stats['pokemon_id'].astype(int)

    # 4. Merge para trazer os nomes
    df_merged = pd.merge(
        df_combats,
        df_pokemons_stats[['pokemon_id', 'name']],
        left_on='pokemon_1_id',
        right_on='pokemon_id',
        how='left'
    ).rename(columns={'name': 'pokemon_1_name'}).drop(columns=['pokemon_id'])

    df_merged = pd.merge(
        df_merged,
        df_pokemons_stats[['pokemon_id', 'name']],
        left_on='pokemon_2_id',
        right_on='pokemon_id',
        how='left'
    ).rename(columns={'name': 'pokemon_2_name'}).drop(columns=['pokemon_id'])

    df_merged = pd.merge(
        df_merged,
        df_pokemons_stats[['pokemon_id', 'name']],
        left_on='winner_id',
        right_on='pokemon_id',
        how='left'
    ).rename(columns={'name': 'winner_name'}).drop(columns=['pokemon_id'])

    # 5. Salvar CSV
    df_merged.to_csv("etl_resultado.csv", index=False)
    print("📂 Dados de combates salvos em etl_resultado.csv")


# ============================================================
# 6. Função Principal
# ============================================================
def main():
    BASE_URL = "http://ec2-54-233-36-108.sa-east-1.compute.amazonaws.com:8000"
    USERNAME = "kaizen-poke"
    PASSWORD = '7`d$t>/ov%ZL8;g~*?Ei&07'

    token = get_jwt_token(BASE_URL, USERNAME, PASSWORD)
    if not token:
        return

    print("\nIniciando extração de combates...")
    combats_list = extract_combats(BASE_URL, token, per_page=10)

    print("\nIniciando extração de pokémons...")
    pokemons_list = extract_pokemons(BASE_URL, token, per_page=50)

    print("\nIniciando extração de detalhes dos pokémons...")
    detalhes_list = extract_pokemon_details(BASE_URL, token, pokemons_list)

    if combats_list and pokemons_list:
        transform_and_load(combats_list, pokemons_list)

        # Salvar Status Pokémons
        df_detalhes = pd.DataFrame(detalhes_list)
        df_detalhes.to_csv("pokemons_detalhes.csv", index=False)
        print(" Dados detalhados dos Pokémons salvos em pokemons_detalhes.csv")
    else:
        print(" Faltaram dados de combates ou pokémons. ETL interrompido.")


if __name__ == "__main__":
    main()
