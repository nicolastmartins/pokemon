import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

# ============================================================
# 1. Carregar os dados
# ============================================================
st.title("📊 Dashboard de Combates Pokémon")

# CSVs
df_combats = pd.read_csv("etl_resultado.csv")
df_pokemons = pd.read_csv("pokemons_detalhes.csv")

st.success("✅ Dados carregados com sucesso!")

st.subheader("Amostra de combates")
st.dataframe(df_combats.head())

st.subheader("Amostra de detalhes dos Pokémons")
st.dataframe(df_pokemons.head())

# ============================================================
# 2. Estatísticas gerais
# ============================================================
total_combates = len(df_combats)
total_pokemons = len(set(df_combats['pokemon_1_name']).union(set(df_combats['pokemon_2_name'])))

st.subheader("📌 Estatísticas Gerais")
col1, col2 = st.columns(2)
col1.metric("Total de Combates", total_combates)
col2.metric("Pokémons Únicos", total_pokemons)

# ============================================================
# 3. Ranking de vitórias
# ============================================================
winners_count = df_combats['winner_name'].value_counts().reset_index()
winners_count.columns = ["pokemon", "vitórias"]

# ============================================================
# 4. Merge de atributos dos Pokémons
# ============================================================
# Status do vencedor
df_winner_stats = pd.merge(
    df_combats,
    df_pokemons[['id','hp','attack','defense','sp_attack','sp_defense','speed','generation','legendary','types']],
    left_on='winner_id',
    right_on='id',
    how='left'
).rename(columns={
    'hp': 'winner_hp',
    'attack': 'winner_attack',
    'defense': 'winner_defense',
    'sp_attack': 'winner_sp_attack',
    'sp_defense': 'winner_sp_defense',
    'speed': 'winner_speed',
    'generation': 'winner_generation',
    'legendary': 'winner_legendary',
    'types': 'winner_types'
}).drop(columns=['id'])

# ============================================================
# 5. Gráficos
# ============================================================
# Top 10 vitórias
st.subheader("📊 Top 10 Pokémons mais Vitoriosos")
top10 = winners_count.head(10)
fig, ax = plt.subplots(figsize=(10,6))
bars = ax.bar(top10['pokemon'], top10['vitórias'], color='orange')
ax.set_ylabel("Vitórias")
ax.set_title("Top 10 Pokémons Vencedores")
ax.set_xticklabels(top10['pokemon'], rotation=45, ha="right")
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height, str(height), ha='center', va='bottom')
st.pyplot(fig)

# ============================================================
# 6. Análises status dos Pokémons
# ============================================================
st.subheader("⚔️ Estatísticas dos Pokémons Vencedores")

# Ataque médio dos vencedores
avg_attack = df_winner_stats['winner_attack'].mean()
st.metric("Ataque médio dos vencedores", round(avg_attack,2))

# Distribuição de velocidade
st.subheader("📈 Distribuição de Velocidade dos Pokémons")
fig, ax = plt.subplots(figsize=(10,6))
ax.hist(df_pokemons['speed'], bins=20, color='skyblue', edgecolor='black')
ax.set_xlabel("Velocidade")
ax.set_ylabel("Quantidade de Pokémons")
st.pyplot(fig)

# Scatter plot Ataque x Defesa dos top 10 vencedores
st.subheader("⚔️ Top 10 vencedores: Ataque x Defesa")
top10_names = winners_count.head(10)['pokemon'].tolist()
top10_winners = df_winner_stats[df_winner_stats['winner_name'].isin(top10_names)]

fig, ax = plt.subplots(figsize=(8,6))
colors = plt.cm.tab10.colors
color_map = {name: colors[i % len(colors)] for i, name in enumerate(top10_names)}

for name in top10_names:
    subset = top10_winners[top10_winners['winner_name'] == name]
    ax.scatter(subset['winner_attack'], subset['winner_defense'],
               color=color_map[name], s=100, label=name)

ax.set_xlabel("Ataque")
ax.set_ylabel("Defesa")
ax.set_title("Ataque vs Defesa dos Top 10 Vencedores")
ax.legend(title="Pokémon", bbox_to_anchor=(1.05, 1), loc='upper left')
st.pyplot(fig)


# ============================================================
# 7. Ranking por taxa de vitória
# ============================================================
combat_count = pd.concat([df_combats['pokemon_1_name'], df_combats['pokemon_2_name']]).value_counts().reset_index()
combat_count.columns = ["pokemon", "combates"]

win_rate = pd.merge(winners_count, combat_count, on="pokemon")
win_rate['taxa_vitoria'] = (win_rate['vitórias'] / win_rate['combates'] * 100).round(2)
win_rate = win_rate.sort_values(by='taxa_vitoria', ascending=False)

st.subheader("🏆 Top 10 Pokémons por Taxa de Vitória")

top10_rate = win_rate.head(10)
fig, ax = plt.subplots(figsize=(10,6))
bars = ax.barh(top10_rate['pokemon'], top10_rate['taxa_vitoria'], color='green', alpha=0.7)
ax.set_xlabel("Taxa de Vitória (%)")
ax.set_title("Top 10 Pokémons por Taxa de Vitória")
ax.invert_yaxis()  # Maior taxa no topo
for bar in bars:
    width = bar.get_width()
    ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{width}%", va='center')
st.pyplot(fig)

# ============================================================
# 8. Confrontos por tipo
# ============================================================
st.subheader("🔥 Heatmap de Confrontos por Tipo")

# Filtrar apenas tipos únicos
df_pokemons_unicos = df_pokemons[~df_pokemons['types'].str.contains("/|,", na=False)]

# Merge dos vencedores
df_winner_types = pd.merge(
    df_combats,
    df_pokemons_unicos[['id','types']],
    left_on='winner_id',
    right_on='id',
    how='left'
).rename(columns={'types':'winner_type'}).drop(columns=['id'])

# Função para buscar tipo do perdedor
def get_loser_type(row):
    loser_id = row['pokemon_1_id'] if row['pokemon_1_id'] != row['winner_id'] else row['pokemon_2_id']
    loser = df_pokemons_unicos.loc[df_pokemons_unicos['id'] == loser_id, 'types']
    return loser.values[0] if len(loser) > 0 else None

df_winner_types['loser_type'] = df_winner_types.apply(get_loser_type, axis=1)

# Remover linhas com tipos ausentes
df_winner_types = df_winner_types.dropna(subset=['winner_type','loser_type'])

# Gerar matriz de vitórias
type_matrix = df_winner_types.groupby(['winner_type','loser_type']).size().reset_index(name='vitórias')
type_matrix_pivot = type_matrix.pivot(index='winner_type', columns='loser_type', values='vitórias').fillna(0).astype(int)

# Heatmap
fig, ax = plt.subplots(figsize=(12,10))
sns.heatmap(
    type_matrix_pivot,
    annot=True,
    fmt='d',
    cmap='YlGnBu',
    cbar_kws={'label': 'Vitórias'},
    linewidths=0.5,
    linecolor='gray',
    ax=ax
)

# Destacar o tipo mais vencido
loser_totals = type_matrix_pivot.sum(axis=0)
tipo_mais_vencido = loser_totals.idxmax()
col_idx = list(type_matrix_pivot.columns).index(tipo_mais_vencido)

ax.set_xlabel("Tipo do Perdedor")
ax.set_ylabel("Tipo do Vencedor")
ax.set_title("Confrontos por Tipo (Tipos Únicos e Simples)")
st.pyplot(fig)
