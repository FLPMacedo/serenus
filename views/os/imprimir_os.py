"""
imprimir_os.py — Gera PDF de uma Ordem de Serviço replicando o layout
visual do template padrão de OS interna (header roxo, seções de
solicitante/descrição/materiais/observações).

Usa xhtml2pdf (já presente no projeto via gerar_pdfs.py).
"""

from __future__ import annotations

import html
from pathlib import Path

from config import formatar_data_exibicao, formatar_moeda
from views.os.os_model import OrdemServico


_STATUS_LABEL = {
    "aberta":          "Aberta",
    "em_andamento":    "Em andamento",
    "aguardando_peca": "Aguardando peça",
    "concluida":       "Concluída",
    "cancelada":       "Cancelada",
}


def _safe(s) -> str:
    """Escapa string para uso seguro em HTML, mantendo nbsp em vazio."""
    if s is None or s == "":
        return "&nbsp;"
    return html.escape(str(s)).replace("\n", "<br/>")


def _fmt_data(data_iso: str | None) -> str:
    if not data_iso:
        return "&nbsp;"
    return formatar_data_exibicao(data_iso)


def _linha_item(item) -> str:
    return (
        "<tr>"
        f"<td>{_safe(item.descricao)}</td>"
        f"<td class='c-num'>{item.quantidade:g}</td>"
        f"<td class='c-num'>{_safe(formatar_moeda(item.preco_unit))}</td>"
        f"<td class='c-num'>{_safe(formatar_moeda(item.subtotal))}</td>"
        f"<td>{_safe(item.observacao)}</td>"
        "</tr>"
    )


def _construir_html(os_: OrdemServico) -> str:
    horas        = os_.horas_trabalhadas
    valor_hora   = os_.valor_hora
    valor_mo     = os_.valor_mao_obra
    total_mat    = os_.total_materiais
    total_geral  = os_.valor_total
    status_label = _STATUS_LABEL.get(os_.status, os_.status)

    if not os_.itens:
        linhas_itens = (
            "<tr><td colspan='5' class='nodata'>"
            "Nenhum material registrado.</td></tr>"
        )
    else:
        linhas_itens = "".join(_linha_item(it) for it in os_.itens)

    mao_obra_label = (
        f"Mão de obra ({horas:g}h × {formatar_moeda(valor_hora)})"
        if horas and valor_hora
        else "Mão de obra"
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  @page {{ size: A4; margin: 1.5cm; }}
  body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt; color: #1F2937;
  }}
  .header {{
    background: #7C3AED;
    color: #FFFFFF;
    text-align: center;
    padding: 10px;
    font-size: 14pt;
    font-weight: bold;
    letter-spacing: 1px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 6px;
  }}
  td, th {{
    border: 1px solid #9CA3AF;
    padding: 5px 8px;
    vertical-align: top;
  }}
  .label-cell {{
    background: #EDE9FE;
    font-weight: bold;
    color: #4C1D95;
    width: 30%;
  }}
  .secao-titulo {{
    background: #DDD6FE;
    color: #4C1D95;
    text-align: center;
    padding: 5px;
    font-weight: bold;
    margin-top: 12px;
    border: 1px solid #C4B5FD;
    border-bottom: 0;
  }}
  .desc-cell {{ height: 80px; }}
  .obs-cell  {{ height: 60px; }}
  .tabela-mat th {{
    background: #DDD6FE;
    color: #4C1D95;
    text-align: left;
  }}
  .c-num    {{ text-align: right; white-space: nowrap; }}
  .nodata   {{ color: #9CA3AF; font-style: italic; text-align: center; }}
  .total-final td {{
    background: #4C1D95;
    color: #FFFFFF;
    font-size: 12pt;
    font-weight: bold;
  }}
  .cabecalho-wrap {{ margin-top: 10px; }}
</style>
</head>
<body>
  <div class="header">ORDEM DE SERVIÇO INTERNA</div>

  <div class="cabecalho-wrap">
  <table>
    <tr>
      <td style="width: 32%; text-align: center; padding: 24px 8px;
                 background: #F5F3FF; color: #6D28D9; font-weight: bold;">
        SERENUS<br/>
        <span style="font-size: 9pt; font-weight: normal;
                     color: #9CA3AF;">Sistema Financeiro</span>
      </td>
      <td style="padding: 0; border: 0;">
        <table style="margin: 0;">
          <tr><td class="label-cell">Nº da Ordem de Serviço</td>
              <td><b>{_safe(os_.numero)}</b></td></tr>
          <tr><td class="label-cell">Status</td>
              <td>{_safe(status_label)}</td></tr>
          <tr><td class="label-cell">Data de solicitação</td>
              <td>{_fmt_data(os_.data_solicitacao)}</td></tr>
          <tr><td class="label-cell">Horário da solicitação</td>
              <td>{_safe(os_.hora_solicitacao)}</td></tr>
          <tr><td class="label-cell">Data de execução</td>
              <td>{_fmt_data(os_.data_execucao)}</td></tr>
          <tr><td class="label-cell">Horário da execução</td>
              <td>{_safe(os_.hora_execucao)}</td></tr>
        </table>
      </td>
    </tr>
  </table>
  </div>

  <div class="secao-titulo">Solicitante</div>
  <table>
    <tr><td class="label-cell">Nome do contato</td>
        <td>{_safe(os_.solicitante_nome)}</td></tr>
    <tr><td class="label-cell">Setor</td>
        <td>{_safe(os_.solicitante_setor)}</td></tr>
    <tr><td class="label-cell">Ramal</td>
        <td>{_safe(os_.solicitante_ramal)}</td></tr>
    <tr><td class="label-cell">Responsável pela execução</td>
        <td>{_safe(os_.responsavel)}</td></tr>
  </table>

  <div class="secao-titulo">Descrição do Serviço</div>
  <table>
    <tr><td class="desc-cell">{_safe(os_.descricao_servico)}</td></tr>
  </table>

  <div class="secao-titulo">Materiais utilizados</div>
  <table class="tabela-mat">
    <tr>
      <th>Item</th>
      <th class="c-num" style="width: 90px;">Quantidade</th>
      <th class="c-num" style="width: 100px;">Valor unit.</th>
      <th class="c-num" style="width: 100px;">Subtotal</th>
      <th>Observações</th>
    </tr>
    {linhas_itens}
  </table>

  <table>
    <tr>
      <td class="label-cell">Total materiais</td>
      <td class="c-num">{_safe(formatar_moeda(total_mat))}</td>
    </tr>
    <tr>
      <td class="label-cell">{_safe(mao_obra_label)}</td>
      <td class="c-num">{_safe(formatar_moeda(valor_mo))}</td>
    </tr>
    <tr class="total-final">
      <td>TOTAL</td>
      <td class="c-num">{_safe(formatar_moeda(total_geral))}</td>
    </tr>
  </table>

  <div class="secao-titulo">Observações gerais</div>
  <table>
    <tr><td class="obs-cell">{_safe(os_.observacoes)}</td></tr>
  </table>
</body>
</html>
"""


def imprimir_os_pdf(os_: OrdemServico, caminho: str | Path) -> Path:
    """Gera um PDF da OS no caminho indicado e retorna o Path final.

    Lança RuntimeError se xhtml2pdf não estiver instalado ou se a
    conversão falhar.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError as e:
        raise RuntimeError(
            "Biblioteca xhtml2pdf não está instalada. "
            "Instale com: pip install xhtml2pdf"
        ) from e

    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    html_str = _construir_html(os_)

    # Escrita atômica: grava num arquivo temporário no mesmo diretório
    # (pra rename ser garantido pelo SO) e só substitui o destino se a
    # conversão sair sem erro. Assim, se pisa.CreatePDF falhar, o PDF
    # anterior (válido) NÃO é apagado nem corrompido.
    import os as _os
    import tempfile as _tempfile
    fd, tmp_path = _tempfile.mkstemp(
        suffix=".pdf", prefix=".tmp_", dir=str(destino.parent),
    )
    try:
        with _os.fdopen(fd, "wb") as f:
            resultado = pisa.CreatePDF(html_str, dest=f, encoding="utf-8")
        if resultado.err:
            raise RuntimeError(
                f"Falha ao gerar PDF da OS {os_.numero}: erro do conversor."
            )
        # Sucesso — substitui atomicamente o destino
        _os.replace(tmp_path, destino)
        tmp_path = None  # marca como já consumido
    finally:
        # Se falhou em qualquer ponto antes do replace, remove o tmp
        if tmp_path is not None:
            try:
                _os.unlink(tmp_path)
            except OSError:
                pass
    return destino
