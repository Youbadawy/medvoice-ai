import React, { useState, useEffect } from 'react';
import {
    Box,
    Heading,
    Text,
    SimpleGrid,
    Stat,
    StatLabel,
    StatNumber,
    StatHelpText,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Card,
    CardHeader,
    CardBody,
    Stack,
    Badge,
    Flex,
    Icon,
    Spinner
} from '@chakra-ui/react';
import { FiDollarSign, FiActivity, FiPhone, FiCpu } from 'react-icons/fi';
import { API_URL } from '../config';

interface CostBreakdown {
    telephony: number;
    asr: number;
    tts: number;
    llm: number;
}

interface DailyCost {
    date: string;
    cost: number;
}

interface CostData {
    period_days: number;
    total_cost: number;
    breakdown: CostBreakdown;
    daily_costs: DailyCost[];
}

const Costs = () => {
    const [data, setData] = useState<CostData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchCosts();
    }, []);

    const fetchCosts = async () => {
        try {
            const response = await fetch(`${API_URL}/admin/costs?days=30`);
            if (response.ok) {
                const jsonData = await response.json();
                setData(jsonData);
            }
        } catch (error) {
            console.error('Error fetching costs:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Flex justify="center" align="center" h="50vh">
                <Spinner size="xl" color="brand.500" />
            </Flex>
        );
    }

    if (!data) {
        return <Text>No cost data available.</Text>;
    }

    return (
        <Box>
            <Heading mb={6} size="lg">Financial Overview (Last 30 Days)</Heading>

            <SimpleGrid columns={{ base: 1, md: 4 }} spacing={6} mb={8}>
                <Card>
                    <CardBody>
                        <Stat>
                            <StatLabel>Total Spend</StatLabel>
                            <StatNumber>${data.total_cost.toFixed(2)}</StatNumber>
                            <StatHelpText>Last 30 Days</StatHelpText>
                        </Stat>
                    </CardBody>
                </Card>

                <Card>
                    <CardBody>
                        <Stat>
                            <StatLabel>Voice & ASR</StatLabel>
                            <StatNumber>${(data.breakdown.telephony + data.breakdown.asr).toFixed(2)}</StatNumber>
                            <StatHelpText>Twilio + Deepgram</StatHelpText>
                        </Stat>
                    </CardBody>
                </Card>

                <Card>
                    <CardBody>
                        <Stat>
                            <StatLabel>AI Brain</StatLabel>
                            <StatNumber>${data.breakdown.llm.toFixed(2)}</StatNumber>
                            <StatHelpText>DeepSeek / GPT-4o</StatHelpText>
                        </Stat>
                    </CardBody>
                </Card>

                <Card>
                    <CardBody>
                        <Stat>
                            <StatLabel>Synthesis (TTS)</StatLabel>
                            <StatNumber>${data.breakdown.tts.toFixed(2)}</StatNumber>
                            <StatHelpText>Google Journey</StatHelpText>
                        </Stat>
                    </CardBody>
                </Card>
            </SimpleGrid>

            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
                <Card>
                    <CardHeader>
                        <Heading size="md">Daily Breakdown</Heading>
                    </CardHeader>
                    <CardBody>
                        <Table variant="simple" size="sm">
                            <Thead>
                                <Tr>
                                    <Th>Date</Th>
                                    <Th isNumeric>Cost (USD)</Th>
                                    <Th>Status</Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                {data.daily_costs.map((day) => (
                                    <Tr key={day.date}>
                                        <Td>{day.date}</Td>
                                        <Td isNumeric fontWeight="bold">${day.cost.toFixed(2)}</Td>
                                        <Td>
                                            <Badge colorScheme={day.cost > 10 ? "red" : day.cost > 2 ? "yellow" : "green"}>
                                                {day.cost > 10 ? "High" : day.cost > 2 ? "Moderate" : "Low"}
                                            </Badge>
                                        </Td>
                                    </Tr>
                                ))}
                                {data.daily_costs.length === 0 && (
                                    <Tr>
                                        <Td colSpan={3} textAlign="center">No usage recorded.</Td>
                                    </Tr>
                                )}
                            </Tbody>
                        </Table>
                    </CardBody>
                </Card>

                <Card>
                    <CardHeader>
                        <Heading size="md">Cost Distribution</Heading>
                    </CardHeader>
                    <CardBody>
                        <Stack spacing={4}>
                            <Box>
                                <Flex justify="space-between" mb={1}>
                                    <Text fontSize="sm">Telephony (Twilio)</Text>
                                    <Text fontSize="sm" fontWeight="bold">${data.breakdown.telephony.toFixed(4)}</Text>
                                </Flex>
                                <Box w="100%" h="2" bg="gray.100" borderRadius="full">
                                    <Box h="100%" bg="blue.400" borderRadius="full" w={`${(data.breakdown.telephony / data.total_cost * 100) || 0}%`} />
                                </Box>
                            </Box>

                            <Box>
                                <Flex justify="space-between" mb={1}>
                                    <Text fontSize="sm">ASR (Deepgram)</Text>
                                    <Text fontSize="sm" fontWeight="bold">${data.breakdown.asr.toFixed(4)}</Text>
                                </Flex>
                                <Box w="100%" h="2" bg="gray.100" borderRadius="full">
                                    <Box h="100%" bg="purple.400" borderRadius="full" w={`${(data.breakdown.asr / data.total_cost * 100) || 0}%`} />
                                </Box>
                            </Box>

                            <Box>
                                <Flex justify="space-between" mb={1}>
                                    <Text fontSize="sm">LLM Intelligence</Text>
                                    <Text fontSize="sm" fontWeight="bold">${data.breakdown.llm.toFixed(4)}</Text>
                                </Flex>
                                <Box w="100%" h="2" bg="gray.100" borderRadius="full">
                                    <Box h="100%" bg="green.400" borderRadius="full" w={`${(data.breakdown.llm / data.total_cost * 100) || 0}%`} />
                                </Box>
                            </Box>

                            <Box>
                                <Flex justify="space-between" mb={1}>
                                    <Text fontSize="sm">Text-to-Speech</Text>
                                    <Text fontSize="sm" fontWeight="bold">${data.breakdown.tts.toFixed(4)}</Text>
                                </Flex>
                                <Box w="100%" h="2" bg="gray.100" borderRadius="full">
                                    <Box h="100%" bg="orange.400" borderRadius="full" w={`${(data.breakdown.tts / data.total_cost * 100) || 0}%`} />
                                </Box>
                            </Box>
                        </Stack>
                    </CardBody>
                </Card>
            </SimpleGrid>
        </Box>
    );
};

export default Costs;
