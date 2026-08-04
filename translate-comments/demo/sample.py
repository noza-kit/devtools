"""このモジュールは挨拶メッセージを組み立てるサンプルです。"""
# [EN] This module is a sample that demonstrates how to construct a greeting message.
# [FR] Ce module est un exemple permettant de composer un message de bienvenue.


class Greeter:
    """挨拶を組み立てるクラス。"""
    # [EN] A class on constructing greetings.
    # [FR] Une classe consacrée à la construction de formules de politesse.

    def greet(self, name):
        """名前を受け取り、挨拶文を返す。"""
        # [EN] Receive the name and reply with a greeting.
        # [FR] Recevoir le nom et répondre par une formule de politesse.
        # 挨拶のベースになる文字列を作る
        # 前後の空白は呼び出し側で調整する想定
        # [EN] Create a base string for the greeting
        # Leading and trailing spaces are to be adjusted by the calling party
        # [FR] Créer une chaîne de caractères servant de base au message d'accueil
        # Les espaces avant et après doivent être ajustés par le programme appelant
        message = "Hello, " + name  # 末尾に感嘆符を付けない方針にした
        # [EN] We've decided on a policy of not adding exclamation points at the end.
        # [FR] Nous avons décidé de ne pas mettre de point d'exclamation à la fin des phrases
        return message


# ---
def main():
    greeter = Greeter()
    print(greeter.greet("World"))


if __name__ == "__main__":
    main()
