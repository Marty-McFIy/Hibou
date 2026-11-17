/* @ds-bundle: {"format":4,"namespace":"Hibou","components":[{"name":"Logo"},{"name":"Logotype"},{"name":"IconeApp"},{"name":"Icone"},{"name":"Reponse"}]} */
(function(){var H="M18 34 L36 12 L52 30 H68 L84 12 L102 34 V74 A42 42 0 0 1 18 74 Z",B="M54 74 L66 74 L60 88 Z";
function svgLogo(o){o=o||{};var v=o.variante?" hb-logo--"+o.variante:"";var c=(o.relief?" hb-logo--relief":"")+(o.vivant?" hb-logo--vivant":"");
return '<svg class="hb-logo'+v+c+'" viewBox="0 0 120 120" role="img" aria-label="'+(o.label||"Hibou")+'"'+(o.etat?' data-etat="'+o.etat+'"':'')+(o.taille?' style="--taille:'+o.taille+'px"':'')+'><g class="hb-logo__corps"><path class="hb-logo__tete" d="'+H+'"/><circle class="hb-logo__orbite" cx="44" cy="60" r="17"/><circle class="hb-logo__orbite" cx="76" cy="60" r="17"/><g class="hb-logo__regard"><circle class="hb-logo__iris" cx="44" cy="60" r="10"/><circle class="hb-logo__iris" cx="76" cy="60" r="10"/><circle class="hb-logo__pupille" cx="44" cy="60" r="4.5"/><circle class="hb-logo__pupille" cx="76" cy="60" r="4.5"/></g><path class="hb-logo__bec" d="'+B+'"/></g></svg>';}
function el(html){var t=document.createElement("template");t.innerHTML=html.trim();return t.content.firstChild;}
var api={
 logoHTML:svgLogo,
 Logo:function(o){return el(svgLogo(o));},
 Logotype:function(o){o=o||{};return el('<span class="hb-logotype" style="--taille:'+(o.taille||64)+'px">'+svgLogo(o)+'<span class="hb-logotype__nom">Hibou</span></span>');},
 IconeApp:function(o){o=o||{};return el('<span class="hb-app'+(o.vivante?' hb-app--vivante':'')+'" style="--taille:'+(o.taille||96)+'px" role="img" aria-label="Hibou">'+svgLogo({variante:"sur-nuit",etat:o.etat})+'</span>');},
 Icone:function(nom,o){o=o||{};return el('<span class="hb-icone hb-icone--'+nom+(o.taille?' hb-icone--'+o.taille:'')+'" aria-hidden="true"></span>');},
 Reponse:function(texte){var p=document.createElement("p");p.className="hb-reponse";texte.split(" ").forEach(function(m,i){var s=document.createElement("span");s.className="hb-reponse__mot";s.style.setProperty("--i",i);s.textContent=m+" ";p.appendChild(s);});return p;},
 etat:function(svg,e){svg.setAttribute("data-etat",e);},
 icones:["ecrire", "document", "dossier", "terminal", "code", "puce", "modele", "disque", "hors-ligne", "verrou", "bouclier", "oeil", "lune", "eclair", "envoyer", "arreter", "copier", "recherche", "reglages", "plus", "fermer", "valider", "alerte", "info", "corbeille", "telecharger", "rafraichir", "historique", "resumer", "corriger", "reformuler", "message", "chevron-droit", "chevron-bas", "menu"]
};
window.Hibou=Object.assign(window.Hibou||{},api);})();
