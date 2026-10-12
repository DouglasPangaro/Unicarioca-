class ErroAplicacao(Exception):
    status_code = 400

    def __init__(self, mensagem: str, **extras):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.extras = extras


class NaoEncontrado(ErroAplicacao):
    status_code = 404


class Conflito(ErroAplicacao):
    status_code = 409


class ArquivoGrande(ErroAplicacao):
    status_code = 413


class Invalido(ErroAplicacao):
    status_code = 422


class ServicoIndisponivel(ErroAplicacao):
    status_code = 503
