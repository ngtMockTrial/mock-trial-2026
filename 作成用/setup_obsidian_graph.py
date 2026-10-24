"""標準グラフの色分けとブックマークを導入する。通常更新とは分ける。"""
import reasoning_graph as graph
from obsidian_graph import configure_graph

if __name__ == '__main__':
    claims, relations = configure_graph(graph.ROOT, graph.load_notes(), graph.refs, graph.availability)
    print(f'OK: {claims}命題・{relations}関係／立場色・関係別のグラフブックマーク5件を設定')
