import pandas as pd
from lxml import etree
import re

xml_file_path = "C:\\Users\\varsh\\Downloads\\CPP_Slides_CM_Data\\CPP_Ericsson_5G_Sample_2_Sites.xml"
parser = etree.XMLParser(recover=True)
tree = etree.parse(xml_file_path, parser)
root = tree.getroot()

namespaces = {
    'es': 'EricssonSpecificAttributes.xsd',
    'xn': 'genericNrm.xsd',
    'un': 'utranNrm.xsd',
    'gn': 'geranNrm.xsd'
}


def get_text(element, tag, ns='es'):
    if element is not None:
        found = element.find(f".//{ns}:{tag}", namespaces)
        return found.text if found is not None else None
    return None


cell_data_list = []
neighbor_data_list = []
sector_carrier_map = {}
sector_attr_map = {}
gnb_id_lookup = {}  #cellID → gNBId
nci_lookup = {}     #cellID → GlobalCellId(nCI)

#build SectorCarrier map
for container in root.findall('.//xn:VsDataContainer', namespaces):
    sector = container.find('./xn:attributes/es:vsDataNRSectorCarrier', namespaces)
    if sector is not None:
        sector_id = get_text(sector, 'nRSectorCarrierId')
        if sector_id:
            sector_carrier_map[sector_id] = get_text(sector, 'frequencyDL')
            sector_attr_map[sector_id] = {
                'Latitude': get_text(sector, 'latitude'),
                'Longitude': get_text(sector, 'longitude'),
                'arfcnUL': get_text(sector, 'arfcnUL'),
                'arfcnDL': get_text(sector, 'arfcnDL')
            }

#extract cell info
for me_context in root.findall('.//xn:MeContext', namespaces):
    gnb_id = None
    mecontext_id = me_context.get('id')

    managed_element = me_context.find('./xn:ManagedElement', namespaces)
    if managed_element is not None:
        for vsdata in managed_element.findall('.//xn:VsDataContainer', namespaces):
            dt = vsdata.find('.//xn:vsDataType', namespaces)
            if dt is not None and dt.text == 'vsDataGNBDUFunction':
                gnb_data = vsdata.find('.//es:vsDataGNBDUFunction', namespaces)
                gnb_id = get_text(gnb_data, 'gNBId')

        for parent_vsdata in managed_element.findall('.//xn:VsDataContainer', namespaces):
            for child_vsdata in parent_vsdata.findall('.//xn:VsDataContainer', namespaces):
                dt_elem = child_vsdata.find('.//xn:vsDataType', namespaces)
                if dt_elem is not None and dt_elem.text == 'vsDataNRCellDU':
                    cell = child_vsdata.find('.//es:vsDataNRCellDU', namespaces)
                    if cell is not None:
                        nCI = get_text(cell, 'nCI')
                        cell_id = get_text(cell, 'nRCellDUId')
                        local_id = get_text(cell, 'cellLocalId')
                        tac = get_text(cell, 'nRTAC')
                        range_ = get_text(cell, 'cellRange')
                        op_state = get_text(cell, 'operationalState')
                        admin_state = get_text(cell, 'administrativeState')

                        freq = sector_carrier_map.get(cell_id)
                        sa = sector_attr_map.get(cell_id, {})

                        cell_data_list.append({
                            'Global Cell ID (nCI)': nCI,
                            'Local Cell ID': local_id,
                            'TAC': tac,
                            'gNBId': gnb_id,
                            'Latitude': sa.get('Latitude'),
                            'Longitude': sa.get('Longitude'),
                            'arfcnUL': sa.get('arfcnUL'),
                            'arfcnDL': sa.get('arfcnDL'),
                            'Frequency Band': freq,
                            'Cell Range': range_,
                            'Operational State': op_state,
                            'Administrative State': admin_state,
                        })

                        if cell_id:
                            gnb_id_lookup[cell_id] = gnb_id
                            nci_lookup[cell_id] = nCI

#extract neighbor relations
for container in root.findall('.//xn:VsDataContainer', namespaces):
    neighbor = container.find('./xn:attributes/es:vsDataNRCellRelation', namespaces)
    if neighbor is not None:
        relation_id = get_text(neighbor, 'nRCellRelationId')
        freq_ref = get_text(neighbor, 'nRFreqRelationRef')

        #extract vsDataNRCellCU from string
        home_cell_id = None
        if freq_ref:
            match = re.search(r'vsDataNRCellCU=([^,]+)', freq_ref)
            if match:
                home_cell_id = match.group(1)

        if home_cell_id and relation_id:
            neighbor_data_list.append({
                'Home gNB ID': gnb_id_lookup.get(home_cell_id),
                'Home Cell ID': home_cell_id,
                'Home Cell Global cell Id': nci_lookup.get(home_cell_id),
                'Neighbor Cell Info': relation_id
            })

pd.DataFrame(cell_data_list).to_csv("C:\\Users\\varsh\\Downloads\\CPP_Slides_CM_Data\\5g_cells_extracted.csv", index=False)
pd.DataFrame(neighbor_data_list).to_csv("C:\\Users\\varsh\\Downloads\\CPP_Slides_CM_Data\\5g_neighbor_cells.csv", index=False)

print("Exported both cell and neighbor data to CSV")
