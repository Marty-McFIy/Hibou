export type EtatHibou = 'veille'|'ecoute'|'reflexion'|'ecriture'|'erreur'|'endormi';
export interface LogoProps { taille?: number; variante?: 'sur-nuit'|'sur-brume'; etat?: EtatHibou; relief?: boolean; vivant?: boolean; label?: string }
export declare function Logo(props?: LogoProps): SVGSVGElement;
export interface LogotypeProps extends LogoProps {}
export declare function Logotype(props?: LogotypeProps): HTMLSpanElement;
export interface IconeAppProps { taille?: number; vivante?: boolean; etat?: EtatHibou }
export declare function IconeApp(props?: IconeAppProps): HTMLSpanElement;
export interface IconeProps { taille?: 'sm'|'lg'|'xl' }
export declare function Icone(nom: string, props?: IconeProps): HTMLSpanElement;
export interface ReponseProps { texte: string }
export declare function Reponse(texte: string): HTMLParagraphElement;
declare global { interface Window { Hibou: { Logo: typeof Logo; Logotype: typeof Logotype; IconeApp: typeof IconeApp; Icone: typeof Icone; Reponse: typeof Reponse; logoHTML(p?: LogoProps): string; etat(svg: SVGSVGElement, e: EtatHibou): void; icones: string[] } } }
