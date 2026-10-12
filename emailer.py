"""Construction et envoi de l'email récapitulatif (SMTP, mot de passe d'application)."""
import html
import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


def build_digest(offers, spontanees, total_spontanees, warnings, max_spontanees):
    """Renvoie (sujet, texte, html). `offers` et `spontanees` : lignes de la base."""
    parts = []
    if offers:
        parts.append(f"{len(offers)} nouvelle(s) offre(s)")
    if total_spontanees:
        parts.append(f"{total_spontanees} entreprise(s) à contacter")
    subject = "[Alternance Guadeloupe] " + " + ".join(parts)

    text = [subject, ""]
    body = ["<h2>Nouvelles offres d'alternance</h2>"] if offers else []

    def line(row):
        return f"- {row['title']} | {row['company'] or '—'} | {row['location'] or '—'}"

    if offers:
        text.append("NOUVELLES OFFRES")
        body.append("<ul>")
        for row in offers:
            text += [line(row), f"  {row['url'] or '(pas de lien)'}", ""]
            link = row["url"] if str(row["url"]).startswith(("http://", "https://")) else ""
            title = html.escape(row["title"])
            if link:
                title = f'<a href="{html.escape(link)}">{title}</a>'
            body.append(
                f"<li><b>{title}</b><br>{html.escape(row['company'] or '—')} · "
                f"{html.escape(row['location'] or '—')}</li>"
            )
        body.append("</ul>")

    if spontanees:
        text.append("ENTREPRISES À CONTACTER (candidature spontanée)")
        body.append("<h2>Candidatures spontanées possibles</h2><ul>")
        for row in spontanees[:max_spontanees]:
            text.append(f"- {row['company']} | {row['location'] or '—'}")
            link = row["url"] if str(row["url"]).startswith(("http://", "https://")) else ""
            name = html.escape(row["company"])
            if link:
                name = f'<a href="{html.escape(link)}">{name}</a>'
            body.append(f"<li>{name} · {html.escape(row['location'] or '—')}</li>")
        body.append("</ul>")
        hidden = total_spontanees - min(total_spontanees, max_spontanees)
        if hidden > 0:
            note = (f"+ {hidden} autres entreprises enregistrées "
                    "(voir `python cli.py list --kind spontanee`).")
            text.append(note)
            body.append(f"<p><i>{html.escape(note)}</i></p>")
        text.append("")

    if warnings:
        text.append("AVERTISSEMENTS")
        body.append("<h3>Avertissements</h3><ul>")
        for w in warnings:
            text.append(f"- {w}")
            body.append(f"<li>{html.escape(w)}</li>")
        body.append("</ul>")

    return subject, "\n".join(text), "\n".join(body)


def send_email(subject: str, text: str, html_body: str) -> bool:
    """Envoie l'email. Renvoie False (sans planter) si SMTP n'est pas configuré ou échoue."""
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    if not (user and password):
        log.warning("SMTP_USER / SMTP_PASSWORD absents : email non envoyé.")
        return False

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    password = password.replace(" ", "")  # Google affiche le mot de passe avec des espaces

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = os.environ.get("EMAIL_TO", user)
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.starttls()
        with server:
            server.login(user, password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as err:
        log.error("Échec de l'envoi de l'email : %s", err)
        return False
    log.info("Email envoyé à %s", msg["To"])
    return True
