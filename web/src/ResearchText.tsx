import type {ReactNode} from 'react';

function safeLink(value:string){
  if(/^\/api\/documents\/[\w-]+\/file(?:#page=\d+)?$/.test(value))return value;
  try{const url=new URL(value);return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password?url.href:null}catch{return null}
}

function Inline({text}:{text:string}){
  return <>{text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^\s)]+\))/g).map((part,index)=>{
    if(part.startsWith('**'))return <strong key={index}>{part.slice(2,-2)}</strong>;
    if(part.startsWith('`'))return <code key={index}>{part.slice(1,-1)}</code>;
    const link=part.match(/^\[([^\]]+)\]\(([^\s)]+)\)$/);
    if(link){const href=safeLink(link[2]);return href?<a key={index} href={href} target="_blank" rel="noopener noreferrer">{link[1]}</a>:link[1]}
    return part;
  })}</>
}

function tableCells(line:string){return line.trim().replace(/^\|/,'').replace(/\|$/,'').split(/(?<!\\)\|/).map(cell=>cell.trim().replace(/\\\|/g,'|'))}
function isTableRule(line:string){return line.includes('|')&&tableCells(line).every(cell=>/^:?-{3,}:?$/.test(cell))}

/** Render the subset used by research notes; model output is never interpreted as HTML. */
export default function ResearchText({text,className=''}:{text:unknown;className?:string}){
  const lines=String(text??'').replace(/\r\n/g,'\n').split('\n');
  const blocks:ReactNode[]=[];
  for(let index=0;index<lines.length;){
    const line=lines[index],key=index;
    if(!line.trim()){index++;continue}
    if(line.trim().startsWith('```')){
      const code:string[]=[];index++;
      while(index<lines.length&&!lines[index].trim().startsWith('```'))code.push(lines[index++]);
      if(index<lines.length)index++;
      blocks.push(<pre key={key}><code>{code.join('\n')}</code></pre>);continue;
    }
    if(index+1<lines.length&&line.includes('|')&&isTableRule(lines[index+1])){
      const headings=tableCells(line),rows:string[][]=[];index+=2;
      while(index<lines.length&&lines[index].includes('|')&&lines[index].trim())rows.push(tableCells(lines[index++]));
      blocks.push(<div className="research-text-table" key={key}><table><thead><tr>{headings.map((cell,i)=><th key={i} scope="col"><Inline text={cell}/></th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{headings.map((_,j)=><td key={j}><Inline text={row[j]||''}/></td>)}</tr>)}</tbody></table></div>);continue;
    }
    const heading=line.match(/^#{1,6}\s+(.+)$/);
    if(heading){blocks.push(<h3 key={key}><Inline text={heading[1]}/></h3>);index++;continue}
    const list=line.match(/^\s*(?:([-*+])|(\d+)[.)、])\s+(.+)$/);
    if(list){
      const ordered=!!list[2],items:string[]=[];let match:RegExpMatchArray|null;
      while(index<lines.length&&(match=lines[index].match(/^\s*(?:([-*+])|(\d+)[.)、])\s+(.+)$/))&&!!match[2]===ordered){items.push(match[3]);index++}
      const nodes=items.map((item,i)=><li key={i}><Inline text={item}/></li>);
      blocks.push(ordered?<ol key={key} start={Number(list[2])}>{nodes}</ol>:<ul key={key}>{nodes}</ul>);continue;
    }
    if(/^>\s?/.test(line)){blocks.push(<blockquote key={key}><Inline text={line.replace(/^>\s?/,'')}/></blockquote>);index++;continue}
    if(/^\s*(?:---+|\*\*\*+)\s*$/.test(line)){blocks.push(<hr key={key}/>);index++;continue}
    blocks.push(<p key={key}><Inline text={line}/></p>);index++;
  }
  return <div className={'research-text '+className}>{blocks}</div>
}
