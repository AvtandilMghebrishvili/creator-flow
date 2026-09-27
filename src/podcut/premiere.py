"""Opt-in offline Lumetri adapter. It never copies Adobe presets into this repository."""
import base64
import copy
import gzip
import uuid
import zlib
from pathlib import Path
import xml.etree.ElementTree as E
from .core import load,write

def patch_luts(project,native,preset,sequence_id,output,closed=False):
    if not closed:
        raise ValueError('Save and close the versioned project copy in Premiere; then supply --closed.')
    p,root=load(project)
    if not p['color'].get('approved') or not p['color']['luts']:
        raise ValueError('This operation needs an approved per-camera LUT look. Original/already-graded footage needs no patch.')
    native,preset,output=Path(native).resolve(),Path(preset).resolve(),Path(output).resolve()
    if output.exists() or native==output:
        raise ValueError('Choose a NEW output .prproj path. Input is never overwritten.')
    document=E.fromstring(gzip.decompress(native.read_bytes()))
    by={n.get('ObjectID'):n for n in document if n.get('ObjectID')}
    uid={n.get('ObjectUID'):n for n in document if n.get('ObjectUID')}
    sequence=uid.get(sequence_id)
    if sequence is None or sequence.tag!='Sequence':raise ValueError('Requested native sequence ID does not exist.')
    group=next(by[x.get('ObjectRef')] for x in sequence.findall('TrackGroups/TrackGroup/Second') if by[x.get('ObjectRef')].tag=='VideoTrackGroup')
    items=[]
    for tr in group.findall('TrackGroup/Tracks/Track'):
        track=uid[tr.get('ObjectURef')]
        items.extend(by[x.get('ObjectRef')] for x in track.findall('ClipTrack/ClipItems/TrackItems/TrackItem'))
    if not items:
        raise ValueError('No video clips found in the selected native sequence; refusing an empty grading operation.')
    presets=E.parse(preset).getroot();pb={n.get('ObjectID'):n for n in presets}
    blobs={x.get('BinaryHash'):x.text for x in presets.iter() if x.get('BinaryHash') and (x.text or '').strip()}
    def payload(node):return node.text or blobs.get(node.get('BinaryHash'),'')
    candidates=[n for n in presets if n.findtext('ParameterID')=='1' and n.find('StartKeyframeValue') is not None and b'FullToSMPTE8' in base64.b64decode(payload(n.find('StartKeyframeValue')))]
    if not candidates:raise ValueError('Unrecognized installed Lumetri preset schema. Use native Lumetri UI/MCP instead.')
    template=next(n for n in presets if n.tag=='VideoFilterComponent' and any(x.get('ObjectRef')==candidates[0].get('ObjectID') for x in n.iter()))
    counter=max(int(n.get('ObjectID','0')) for n in document)+1
    count=0
    for item in items:
        sub=by[item.find('ClipTrackItem/SubClip').get('ObjectRef')]
        camera=(sub.findtext('Name') or '').split('|')[0].strip()
        if camera not in p['color']['luts']:
            raise ValueError(f'Unrecognized clip/source prefix {camera}; refusing partial grading.')
        chain=by[item.find('ClipTrackItem/ComponentOwner/Components').get('ObjectRef')]
        components=chain.find('ComponentChain/Components')
        if components is None:components=E.SubElement(chain.find('ComponentChain'),'Components',Version='1')
        if any(by[x.get('ObjectRef')].findtext('MatchName')=='AE.ADBE Lumetri' for x in components):
            raise ValueError('Sequence already contains Lumetri. Inspect it; do not stack or overwrite grades automatically.')
        lut=str(Path(p['color']['luts'][camera]).resolve())
        if not Path(lut).is_file():raise ValueError('Approved LUT is missing')
        component=copy.deepcopy(template);cid=str(counter);counter+=1;component.set('ObjectID',cid)
        component.find('Component/ID').text='3'
        for ref in component.findall('.//Param'):
            par=copy.deepcopy(pb[ref.get('ObjectRef')]);par.set('ObjectID',str(counter));ref.set('ObjectRef',str(counter));counter+=1
            value=par.find('StartKeyframeValue')
            if value is not None and value.get('Encoding')=='base64':
                value.text=payload(value)
                value.attrib.pop('BinaryHash',None)
            pid=par.findtext('ParameterID')
            if pid=='1':
                doc=E.fromstring(base64.b64decode(value.text))
                doc.find('guid').text='"'+str(uuid.uuid4())+'"'
                targets=[x for x in doc.findall('.//LUT') if 'FullToSMPTE8' in (x.text or '')]
                if not targets:raise ValueError('Unknown Lumetri input LUT slot')
                for x in targets:x.text='"'+lut+'"'
                value.text=base64.b64encode(E.tostring(doc,encoding='utf-8')).decode()
            elif pid=='4':value.text=base64.b64encode((lut+'\0').encode('utf-16-le')).decode()
            if value is not None and value.get('Encoding')=='base64' and value.text:
                value.set('Checksum',str(zlib.crc32(base64.b64decode(value.text))))
            document.append(par)
        document.append(component)
        E.SubElement(components,'Component',Index=str(len(components)),ObjectRef=cid)
        count+=1
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(gzip.compress(E.tostring(document,encoding='utf-8',xml_declaration=True)))
    write(root/'native_patch_receipt.json',{'input':str(native),'output':str(output),'sequence_id':sequence_id,'clips':count,'native_reopen_verified':False,
                                          'next':'Open output in Premiere, save, reopen, verify all clips/colors and separate audio. This receipt alone does not certify native compatibility.'})
    return output
